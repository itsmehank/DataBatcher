from datetime import datetime
import xml.etree.ElementTree as ET

import mysql.connector
import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from mysql.connector import Error


class RealEstateDataManager:
    """
    국토교통부 연립다세대 매매 실거래가 API와 상호작용하고,
    분석에 필요한 지표를 계산하여 MySQL 데이터베이스에 저장하는 클래스.
    데이터 수집 로그를 통해 중복 작업을 방지하고, 트랜잭션을 통해 데이터 무결성을 보장합니다.
    """

    API_BASE_URL = "http://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade"

    def __init__(self, api_key, db_config):
        self.api_key = api_key
        self.db_config = db_config
        now = datetime.now()
        self.latest_months = [
            now.strftime("%Y%m"),
            (now - relativedelta(months=1)).strftime("%Y%m"),
        ]

    def _get_db_connection(self):
        try:
            return mysql.connector.connect(**self.db_config, autocommit=False)
        except Error as e:
            print(f"데이터베이스 연결 중 오류 발생: {e}")
            return None

    def setup_database(self, main_table_name="rh_trade_analysis"):
        from project_config import ensure_schema
        ensure_schema(self.db_config)

    def _is_ingestion_logged(self, cursor, lawd_cd, deal_ymd):
        query = "SELECT 1 FROM data_ingestion_log WHERE lawd_cd = %s AND deal_ymd = %s"
        cursor.execute(query, (lawd_cd, deal_ymd))
        return cursor.fetchone() is not None

    def _get_api_data(self, lawd_cd, deal_ymd):
        params = {"serviceKey": self.api_key, "LAWD_CD": lawd_cd, "DEAL_YMD": deal_ymd, "numOfRows": "1000"}
        try:
            response = requests.get(self.API_BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            result_code = root.findtext("./header/resultCode")
            if result_code not in ["00", "000"]:
                print(f"API 오류: {root.findtext('./header/resultMsg')} (코드: {result_code}) - {lawd_cd}, {deal_ymd}")
                return []
            items_element = root.find("./body/items")
            if items_element is None:
                return []
            return [
                {child.tag: child.text.strip() if child.text else "" for child in item}
                for item in items_element.findall("item")
            ]
        except (requests.exceptions.RequestException, ET.ParseError) as e:
            print(f"API 데이터 조회 중 오류 발생 ({lawd_cd}, {deal_ymd}): {e}")
            return None

    def _process_and_insert_data(self, connection, lawd_cd, deal_ymd, table_name):
        with connection.cursor() as cursor:
            is_latest = deal_ymd in self.latest_months
            if not is_latest and self._is_ingestion_logged(cursor, lawd_cd, deal_ymd):
                print(f"[{lawd_cd}-{deal_ymd}] 이미 처리된 데이터입니다. 건너뜁니다.")
                return True

            api_data = self._get_api_data(lawd_cd, deal_ymd)
            if api_data is None:
                return False
            if not api_data:
                print(f"[{lawd_cd}-{deal_ymd}] 조회된 데이터가 없습니다.")
                log_query = """
                            INSERT INTO data_ingestion_log (lawd_cd, deal_ymd, record_count)
                            VALUES (%s, %s, %s) ON DUPLICATE KEY
                            UPDATE record_count =
                            VALUES (record_count), status = 'SUCCESS'
                            """
                cursor.execute(log_query, (lawd_cd, deal_ymd, 0))
                return True

            processed_data = []
            pyeong = 3.3058
            for item in api_data:
                if item.get("cdealType", "").strip():
                    continue
                try:
                    deal_amount = int(item.get("dealAmount", "0").replace(",", ""))
                    exclu_ar = float(item.get("excluUseAr", 0.0))
                    land_ar = float(item.get("landAr", 0.0))
                    processed_data.append(
                        {
                            "sggCd": item.get("sggCd"),
                            "umdNm": item.get("umdNm"),
                            "mhouseNm": item.get("mhouseNm"),
                            "jibun": item.get("jibun"),
                            "buildYear": int(item.get("buildYear", 0)),
                            "excluUseAr": exclu_ar,
                            "landAr": land_ar,
                            "dealYear": int(item.get("dealYear", 0)),
                            "dealMonth": int(item.get("dealMonth", 0)),
                            "dealDay": int(item.get("dealDay", 0)),
                            "dealAmount": deal_amount,
                            "floor": int(item.get("floor", 0)),
                            "dealingGbn": item.get("dealingGbn"),
                            "estateAgentSggNm": item.get("estateAgentSggNm"),
                            "rgstDate": item.get("rgstDate"),
                            "slerGbn": item.get("slerGbn"),
                            "buyerGbn": item.get("buyerGbn"),
                            "price_per_pyeong": (deal_amount / exclu_ar) * pyeong if exclu_ar > 0 else 0,
                            "land_price_per_pyeong": (deal_amount / land_ar) * pyeong if land_ar > 0 else 0,
                            "land_share_ratio": (land_ar / exclu_ar) if exclu_ar > 0 else 0,
                        }
                    )
                except (ValueError, TypeError) as e:
                    print(f"데이터 처리 중 오류: {e}, 항목: {item}")

            try:
                if is_latest:
                    delete_query = f"DELETE FROM {table_name} WHERE sggCd = %s AND dealYear = %s AND dealMonth = %s"
                    year, month = int(deal_ymd[:4]), int(deal_ymd[4:])
                    cursor.execute(delete_query, (lawd_cd, year, month))
                    print(f"[{lawd_cd}-{deal_ymd}] 최신 월 데이터 갱신을 위해 기존 데이터를 삭제했습니다. ({cursor.rowcount} 건)")

                if processed_data:
                    insert_query = f"""
                    INSERT IGNORE INTO {table_name} (
                        sggCd, umdNm, mhouseNm, jibun, buildYear, excluUseAr, landAr, dealYear, dealMonth, dealDay,
                        dealAmount, floor, dealingGbn, estateAgentSggNm, rgstDate, slerGbn, buyerGbn,
                        price_per_pyeong, land_price_per_pyeong, land_share_ratio
                    ) VALUES (
                        %(sggCd)s, %(umdNm)s, %(mhouseNm)s, %(jibun)s, %(buildYear)s, %(excluUseAr)s, %(landAr)s,
                        %(dealYear)s, %(dealMonth)s, %(dealDay)s, %(dealAmount)s, %(floor)s, %(dealingGbn)s,
                        %(estateAgentSggNm)s, %(rgstDate)s, %(slerGbn)s, %(buyerGbn)s, %(price_per_pyeong)s,
                        %(land_price_per_pyeong)s, %(land_share_ratio)s
                    )"""
                    cursor.executemany(insert_query, processed_data)
                    print(f"[{lawd_cd}-{deal_ymd}] 신규 데이터 {cursor.rowcount}건을 삽입했습니다.")

                log_query = """
                            INSERT INTO data_ingestion_log (lawd_cd, deal_ymd, record_count)
                            VALUES (%s, %s, %s) ON DUPLICATE KEY
                            UPDATE record_count =
                            VALUES (record_count), status = 'SUCCESS'
                            """
                cursor.execute(log_query, (lawd_cd, deal_ymd, len(processed_data)))

                return True
            except Error as e:
                print(f"DB 작업 중 오류 발생 ({lawd_cd}-{deal_ymd}): {e}")
                return False

    def run_ingestion(self, lawd_cds, start_deal_ymd, end_deal_ymd, table_name="rh_trade_analysis"):
        with self._get_db_connection() as connection:
            if not connection:
                print("DB 연결 실패. 작업을 중단합니다.")
                return

            date_range = pd.date_range(
                start=datetime.strptime(start_deal_ymd, "%Y%m"),
                end=datetime.strptime(end_deal_ymd, "%Y%m"),
                freq="MS",
            ).strftime("%Y%m").tolist()

            for lawd_cd in lawd_cds:
                print(f"\n--- {lawd_cd} 지역 작업 시작 ({start_deal_ymd}~{end_deal_ymd}) ---")
                for deal_ymd in date_range:
                    success = self._process_and_insert_data(connection, lawd_cd, deal_ymd, table_name)
                    if success:
                        connection.commit()
                    else:
                        connection.rollback()
                        print(f"[{lawd_cd}-{deal_ymd}] 작업 실패. 롤백되었습니다.")
                print(f"--- {lawd_cd} 지역 작업 완료 ---")
