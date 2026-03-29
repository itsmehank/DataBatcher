import argparse
import os
from datetime import datetime
from pathlib import Path

from dateutil.relativedelta import relativedelta

from project_config import ensure_schema, find_available_port, get_db_config, get_env_str, validate_db_env  # noqa: F401
from src.real_estate.analysis import RealEstateAnalyzer
from src.real_estate.analyzers.above_ground import AboveGroundBuildingAnalyzer
from src.real_estate.analyzers.below_ground import BelowGroundBuildingAnalyzer
from src.real_estate.backend import get_web_app
from src.real_estate.ingestion import RealEstateDataManager
from src.real_estate.processing import DataAnomalyCorrector, DataRecalculator
from utils import load_json_to_dict


APP_ROOT = Path(__file__).resolve().parents[2]


def _parse_ymd(value: str) -> str:
    datetime.strptime(value, "%Y%m")
    return value


def _load_lawd_codes(path: str):
    data = load_json_to_dict(path)
    if not data:
        raise ValueError(f"구 코드 파일을 읽을 수 없습니다: {path}")
    return [gu["code"] for gu in data.get("seoul_top10_gu_codes", [])]


def run_init_db(_args):
    db_config = get_db_config()
    ensure_schema(db_config)
    print("init-db 완료: 수집/분석/시각화용 테이블 준비 완료")


def run_ingest(args):
    db_config = get_db_config()
    api_key = get_env_str("RE_API_SERVICE_KEY", "")
    if not api_key:
        raise ValueError("RE_API_SERVICE_KEY 환경 변수가 필요합니다.")

    if args.lawd_cds:
        lawd_cds = [code.strip() for code in args.lawd_cds.split(",") if code.strip()]
    else:
        lawd_cds = _load_lawd_codes(args.gu_codes_file)

    manager = RealEstateDataManager(api_key=api_key, db_config=db_config)
    manager.run_ingestion(
        lawd_cds=lawd_cds,
        start_deal_ymd=args.start_ymd,
        end_deal_ymd=args.end_ymd,
        table_name="rh_trade_analysis",
    )


def run_analyze(args):
    db_config = get_db_config()

    if not args.skip_monthly:
        monthly_analyzer = RealEstateAnalyzer(db_config=db_config)
        monthly_analyzer.run_analysis(source_table="rh_trade_analysis", target_table="monthly_dong_analysis")

    if not args.skip_floor:
        above_analyzer = AboveGroundBuildingAnalyzer(db_config=db_config)
        above_analyzer.run_analysis(
            source_table="rh_trade_analysis",
            target_table="building_transaction_analysis_above_ground",
        )

        below_analyzer = BelowGroundBuildingAnalyzer(db_config=db_config)
        below_analyzer.run_analysis(
            source_table="rh_trade_analysis",
            target_table="building_transaction_analysis_below_ground",
        )


def run_clean_anomalies(_args):
    db_config = get_db_config()
    corrector = DataAnomalyCorrector(db_config)
    corrector.correct_land_area_anomalies()


def run_recalculate(_args):
    db_config = get_db_config()
    recalculator = DataRecalculator(db_config)
    recalculator.recalculate_and_update_all()


def run_serve_web(args):
    validate_db_env()
    preferred_port = args.port
    run_port = find_available_port(preferred_port)

    app = get_web_app(test_mode=args.test_mode)

    print(f"웹 서버 실행 포트: {run_port}")
    app.run(debug=args.debug, host=args.host, port=run_port)


def run_validate_config(args):
    validate_db_env()
    if args.require_api_key and not get_env_str("RE_API_SERVICE_KEY", ""):
        raise ValueError("RE_API_SERVICE_KEY 환경 변수가 필요합니다.")
    print("설정 검증 완료: 필요한 환경 변수가 준비되었습니다.")


def build_parser():
    parser = argparse.ArgumentParser(description="RealEstateProject 운영 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db = subparsers.add_parser("init-db", help="외부 DB에 필요한 테이블 초기화")
    init_db.set_defaults(func=run_init_db)

    ingest = subparsers.add_parser("ingest", help="API에서 거래 데이터 수집/적재")
    ingest.add_argument("--start-ymd", default=(datetime.now() - relativedelta(years=20)).strftime("%Y%m"), type=_parse_ymd)
    ingest.add_argument("--end-ymd", default=datetime.now().strftime("%Y%m"), type=_parse_ymd)
    ingest.add_argument("--lawd-cds", default="", help="콤마 구분 지역코드 목록(예: 11650,11710)")
    ingest.add_argument("--gu-codes-file", default=str(APP_ROOT / "gu_codes.json"))
    ingest.set_defaults(func=run_ingest)

    analyze = subparsers.add_parser("analyze", help="적재 데이터를 분석 테이블로 변환")
    analyze.add_argument("--skip-monthly", action="store_true", help="동단위 월분석 생략")
    analyze.add_argument("--skip-floor", action="store_true", help="지상/지하 건물분석 생략")
    analyze.set_defaults(func=run_analyze)

    clean = subparsers.add_parser("clean-anomalies", help="원천 데이터 이상치(대지권) 보정")
    clean.set_defaults(func=run_clean_anomalies)

    recalc = subparsers.add_parser("recalculate-derived", help="원천 데이터 파생 컬럼 재계산")
    recalc.set_defaults(func=run_recalculate)

    serve = subparsers.add_parser("serve-web", help="시각화 웹 서버 실행")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=5001)
    serve.add_argument("--debug", action="store_true")
    serve.add_argument("--test-mode", action="store_true", help="더미 데이터 테스트 서버 실행")
    serve.set_defaults(func=run_serve_web)

    validate = subparsers.add_parser("validate-config", help="환경 설정 유효성 검사")
    validate.add_argument("--require-api-key", action="store_true")
    validate.set_defaults(func=run_validate_config)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
