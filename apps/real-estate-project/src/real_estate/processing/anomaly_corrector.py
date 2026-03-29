import json
from pathlib import Path

import mysql.connector
from mysql.connector import Error


class DataAnomalyCorrector:
    """
    rh_trade_analysis 테이블에서 대지권(landAr)이 비정상적으로 큰
    데이터 이상치를 찾아 보정하는 클래스.
    """

    def __init__(self, db_config):
        self.db_config = db_config
        self.gu_code_map = self._load_gu_codes()

    def _load_gu_codes(self):
        try:
            project_root = Path(__file__).resolve().parents[3]
            gu_codes_path = project_root / "gu_codes.json"

            with open(gu_codes_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            code_map = {}
            for gu in data["seoul_top10_gu_codes"]:
                code_map[gu["code"]] = gu["name"]
            return code_map
        except Exception as e:
            print(f"구 코드 파일 로딩 실패: {e}")
            return {}

    def _get_db_connection(self):
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as e:
            print(f"데이터베이스 연결 중 오류 발생: {e}")
            return None

    def correct_land_area_anomalies(self):
        connection = self._get_db_connection()
        if not connection:
            return

        cursor = connection.cursor(dictionary=True)

        try:
            find_anomalies_query = """
                                   SELECT id,
                                          sggCd,
                                          umdNm,
                                          jibun,
                                          buildYear,
                                          floor,
                                          excluUseAr,
                                          landAr
                                   FROM rh_trade_analysis
                                   WHERE excluUseAr > 0
                                     AND landAr > 0
                                     AND landAr >= (excluUseAr * 2);
                                   """
            cursor.execute(find_anomalies_query)
            anomalies = cursor.fetchall()
            print(f"총 {len(anomalies)}건의 이상 데이터 후보를 찾았습니다. 검증 및 수정을 시작합니다.")

            print("\n=== 이상 데이터 목록 ===")
            for i, anomaly in enumerate(anomalies, 1):
                gu_name = self.gu_code_map.get(anomaly["sggCd"], f"코드{anomaly['sggCd']}")
                ratio = anomaly["landAr"] / anomaly["excluUseAr"]
                print(
                    f"{i:2d}. [ID:{anomaly['id']:6}] {gu_name} {anomaly['umdNm']} {anomaly['jibun']} "
                    f"| 건축:{anomaly['buildYear']} | {anomaly['floor']:2}층 "
                    f"| 전용:{anomaly['excluUseAr']:6.2f}㎡ | 대지권:{anomaly['landAr']:6.2f}㎡ | 비율:{ratio:4.1f}배"
                )
            print("=" * 100)

            updated_count = 0
            for anomaly in anomalies:
                find_unit_transactions_query = """
                                               SELECT excluUseAr, landAr
                                               FROM rh_trade_analysis
                                               WHERE sggCd = %s
                                                 AND umdNm = %s
                                                 AND jibun = %s
                                                 AND buildYear = %s
                                                 AND floor = %s;
                                               """
                params = (anomaly["sggCd"], anomaly["umdNm"], anomaly["jibun"], anomaly["buildYear"], anomaly["floor"])
                cursor.execute(find_unit_transactions_query, params)
                all_transactions = cursor.fetchall()

                if len(all_transactions) < 2:
                    continue

                correct_land_ar = None
                for tx in all_transactions:
                    is_normal = tx["landAr"] < (tx["excluUseAr"] * 2)
                    if is_normal and tx["excluUseAr"] == anomaly["excluUseAr"]:
                        correct_land_ar = tx["landAr"]
                        break

                if correct_land_ar is not None:
                    update_query = "UPDATE rh_trade_analysis SET landAr = %s WHERE id = %s;"
                    cursor.execute(update_query, (correct_land_ar, anomaly["id"]))
                    print(
                        f"  [수정] ID: {anomaly['id']}의 landAr 값을 {anomaly['landAr']} -> {correct_land_ar} (으)로 변경했습니다."
                    )
                    updated_count += 1

            connection.commit()
            print(f"\n총 {updated_count}건의 데이터가 성공적으로 수정되었습니다.")

        except Error as e:
            print(f"작업 중 오류 발생: {e}")
            connection.rollback()
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("데이터베이스 연결을 닫았습니다.")
