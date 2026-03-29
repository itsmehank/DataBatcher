import calendar
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from dateutil.relativedelta import relativedelta
from flask import Flask, jsonify, render_template, request

from building_query.building_transaction_query import BuildingTransactionQuery
from map_drawing import map_utils
from project_config import get_db_config, get_env_str, get_flask_secret
from src.real_estate.detectors import CombinedSurgeDetector, DistrictSurgeDetector


def create_app():
    project_root = Path(__file__).resolve().parents[3]
    template_dir = project_root / "web_ui" / "templates"
    static_dir = project_root / "web_ui" / "static"
    gu_codes_path = project_root / "gu_codes.json"

    app = Flask(__name__, template_folder=str(template_dir), static_folder=str(static_dir))
    app.secret_key = get_flask_secret()
    db_connection_info = get_db_config()
    kakao_js_key = get_env_str("KAKAO_JS_KEY", "")
    max_result_limit = 10

    def load_gu_codes():
        try:
            with open(gu_codes_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [item["name"] for item in data["seoul_top10_gu_codes"]]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return [
                "송파구",
                "강남구",
                "서초구",
                "용산구",
                "성동구",
                "광진구",
                "마포구",
                "동작구",
                "영등포구",
                "강동구",
            ]

    @app.route("/")
    @app.route("/v2")
    def index():
        gu_list = load_gu_codes()
        return render_template("index_console.html", gu_list=gu_list, kakao_js_key=kakao_js_key)

    def _normalize_result_rows(results_df):
        results_dict = results_df.to_dict(orient="records")
        for record in results_dict:
            if "surge_score" in record and record["surge_score"]:
                record["surge_score"] = round(float(record["surge_score"]), 2)
            if "avg_dealAmount" in record and record["avg_dealAmount"]:
                record["avg_dealAmount"] = int(record["avg_dealAmount"])
        return results_dict

    def _limit_result_rows(results_dict, limit=max_result_limit):
        total_count = len(results_dict)
        limited = results_dict[:limit]
        return limited, total_count

    @app.route("/combined_analysis", methods=["POST"])
    def combined_analysis():
        try:
            data = request.get_json() or {}
            target_ymd = data.get("target_ymd")
            if not target_ymd:
                raise ValueError("target_ymd 값이 필요합니다.")
            top_percent = float(data.get("top_percent", 1.0))
            analysis_period = int(data.get("analysis_period", 6))

            datetime.strptime(target_ymd, "%Y%m")

            detector = CombinedSurgeDetector(db_connection_info)
            results = detector.find_surging_properties(
                target_ymd=target_ymd,
                top_percent=top_percent,
                analysis_period_months=analysis_period,
            )

            if results.empty:
                return jsonify(
                    {
                        "success": True,
                        "message": "분석 기간 내 급등 신호가 포착된 건물이 없습니다.",
                        "data": [],
                    }
                )

            results_dict = _normalize_result_rows(results)
            results_dict, total_count = _limit_result_rows(results_dict)
            results_dict = map_utils.enrich_records_with_coords(results_dict, limit=max_result_limit)

            if total_count > max_result_limit:
                message = f"총 {total_count}개의 급등 후보 중 상위 {max_result_limit}개만 표시합니다."
            else:
                message = f"총 {len(results_dict)}개의 급등 후보 건물을 표시합니다."

            response_data = {
                "success": True,
                "message": message,
                "data": results_dict,
            }
            return jsonify(response_data)
        except ValueError:
            return jsonify({"success": False, "error": "입력값이 올바르지 않습니다. 날짜 형식(YYYYMM)을 확인해주세요."})
        except Exception as e:
            print(f"[combined_analysis] 오류: {e}")
            return jsonify({"success": False, "error": "분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."})

    @app.route("/district_analysis", methods=["POST"])
    def district_analysis():
        try:
            data = request.get_json() or {}
            target_ymd = data.get("target_ymd")
            if not target_ymd:
                raise ValueError("target_ymd 값이 필요합니다.")
            gu_name = data.get("gu_name") or ""
            district_name = data.get("district_name")
            top_n = int(data.get("top_n", 10))
            analysis_period = int(data.get("analysis_period", 6))

            datetime.strptime(target_ymd, "%Y%m")

            if district_name:
                detector = DistrictSurgeDetector(db_connection_info)
                results = detector.find_surging_properties(
                    target_ymd=target_ymd,
                    district_name=district_name,
                    top_n=top_n,
                    analysis_period_months=analysis_period,
                )
                analysis_area = district_name
            else:
                detector = CombinedSurgeDetector(db_connection_info)
                gu_codes = {
                    "송파구": "11710",
                    "강남구": "11680",
                    "서초구": "11650",
                    "용산구": "11170",
                    "성동구": "11200",
                    "광진구": "11215",
                    "마포구": "11440",
                    "동작구": "11590",
                    "영등포구": "11560",
                    "강동구": "11740",
                }
                gu_code = gu_codes.get(gu_name)
                if not gu_code:
                    return jsonify({"success": False, "error": f"지원하지 않는 구 이름입니다: {gu_name}"})

                results = detector.find_surging_properties(
                    target_ymd=target_ymd,
                    top_percent=100.0,
                    analysis_period_months=analysis_period,
                    sgg_cd_filter=gu_code,
                    top_n=top_n,
                )
                analysis_area = gu_name

            if results.empty:
                return jsonify(
                    {
                        "success": True,
                        "message": f"{analysis_area} 분석 기간 내 급등 신호가 포착된 건물이 없습니다.",
                        "data": [],
                    }
                )

            results_dict = _normalize_result_rows(results)
            results_dict, total_count = _limit_result_rows(results_dict)
            results_dict = map_utils.enrich_records_with_coords(results_dict, limit=max_result_limit)

            if total_count > max_result_limit:
                message = f"{analysis_area}에서 총 {total_count}개의 급등 후보 중 상위 {max_result_limit}개만 표시합니다."
            else:
                message = f"{analysis_area}에서 총 {len(results_dict)}개의 급등 후보 건물을 표시합니다."

            response_data = {
                "success": True,
                "message": message,
                "data": results_dict,
            }
            return jsonify(response_data)
        except ValueError:
            return jsonify({"success": False, "error": "입력값이 올바르지 않습니다. 날짜 형식(YYYYMM)을 확인해주세요."})
        except Exception as e:
            print(f"[district_analysis] 오류: {e}")
            return jsonify({"success": False, "error": "분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."})

    @app.route("/get_districts", methods=["GET"])
    def get_districts():
        gu_name = request.args.get("gu") or ""
        sample_districts = {
            "송파구": ["송파동", "잠실동", "문정동", "석촌동"],
            "강남구": ["압구정동", "청담동", "신사동", "논현동", "역삼동"],
            "서초구": ["반포동", "서초동", "방배동", "양재동"],
            "용산구": ["한남동", "이태원동", "용산동", "남영동"],
            "성동구": ["성수동", "왕십리동", "행당동", "금호동"],
            "광진구": ["자양동", "구의동", "광장동", "중곡동"],
            "마포구": ["상암동", "합정동", "홍대앞", "연남동"],
            "동작구": ["사당동", "대방동", "신대방동", "상도동"],
            "영등포구": ["여의도동", "당산동", "영등포동", "신길동"],
            "강동구": ["천호동", "성내동", "강일동", "둔촌동"],
        }
        return jsonify({"districts": sample_districts.get(gu_name, [])})

    @app.route("/building_detail")
    def building_detail():
        try:
            sgg_cd = request.args.get("sggCd") or ""
            umd_nm = request.args.get("umdNm") or ""
            jibun = request.args.get("jibun") or ""
            build_year = request.args.get("buildYear") or ""
            analysis_type = request.args.get("analysisType")
            target_ymd = request.args.get("targetYmd")
            analysis_period = int(request.args.get("analysisPeriod", "6") or "6")

            if not all([sgg_cd, umd_nm, jibun, build_year, target_ymd]):
                return "필수 파라미터가 누락되었습니다.", 400

            target_ymd = str(target_ymd)
            build_year_int = int(build_year)

            end_date = datetime.strptime(target_ymd, "%Y%m")
            start_date = end_date - relativedelta(months=analysis_period - 1)
            start_date_str = start_date.strftime("%Y-%m-01")
            end_day = calendar.monthrange(end_date.year, end_date.month)[1]
            end_date_str = end_date.strftime(f"%Y-%m-{end_day:02d}")

            building_query = BuildingTransactionQuery(db_connection_info)

            transactions = building_query.get_building_transactions(
                sgg_cd=sgg_cd,
                umd_nm=umd_nm,
                jibun=jibun,
                build_year=build_year_int,
                start_date=start_date_str,
                end_date=end_date_str,
            )

            all_transactions = building_query.get_building_transactions(
                sgg_cd=sgg_cd,
                umd_nm=umd_nm,
                jibun=jibun,
                build_year=build_year_int,
            )

            summary = building_query.get_building_summary(
                sgg_cd=sgg_cd,
                umd_nm=umd_nm,
                jibun=jibun,
                build_year=build_year_int,
            )

            map_record = {"sggCd": sgg_cd, "umdNm": umd_nm, "jibun": jibun}
            enriched_map_record = map_utils.enrich_records_with_coords([map_record], limit=1)[0]
            address = enriched_map_record.get("address")
            lat = enriched_map_record.get("lat")
            lng = enriched_map_record.get("lng")

            context = {
                "building_info": {
                    "sgg_cd": sgg_cd,
                    "umd_nm": umd_nm,
                    "jibun": jibun,
                    "build_year": build_year,
                    "mhouse_nm": summary["building_info"]["mhouse_nm"] if summary["total_transactions"] > 0 else f"({jibun})",
                },
                "analysis_info": {
                    "type": analysis_type,
                    "target_ymd": target_ymd,
                    "analysis_period": analysis_period,
                    "start_date": start_date.strftime("%Y-%m"),
                    "end_date": end_date.strftime("%Y-%m"),
                },
                "analysis_transactions": transactions.to_dict(orient="records") if not transactions.empty else [],
                "all_transactions": all_transactions.to_dict(orient="records") if not all_transactions.empty else [],
                "summary": summary,
                "kakao_js_key": kakao_js_key,
                "map_info": {
                    "address": address,
                    "lat": lat,
                    "lng": lng,
                },
            }
            return render_template("building_detail.html", **context)
        except Exception as e:
            print(f"[building_detail] 오류: {e}")
            return "요청을 처리할 수 없습니다. 잠시 후 다시 시도해주세요.", 500

    return app
