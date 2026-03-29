from datetime import datetime

import mysql.connector
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from mysql.connector import Error

from surge_score_utils import calculate_surge_score


class DistrictSurgeDetector:
    """
    특정 동(district)에 대한 급등 건물을 상위 N개 반환합니다.
    """

    def __init__(self, db_config):
        self.db_config = db_config

    def _get_db_connection(self):
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as e:
            print(f"데이터베이스 연결 중 오류 발생: {e}")
            return None

    def _get_data_from_table(self, table_name, start_ymd, target_ymd, floor_type, district_name):
        query = f"""
        SELECT
            sggCd, umdNm, jibun, buildYear, mhouseNm, deal_ymd,
            trade_count, avg_dealAmount,
            avg_exclu_price_per_pyeong, exclu_price_change_rate_vs_prev,
            avg_land_price_per_pyeong, land_price_change_rate_vs_prev
        FROM {table_name}
        WHERE umdNm = %s
        AND (sggCd, jibun, buildYear) IN (
            SELECT sggCd, jibun, buildYear
            FROM {table_name}
            WHERE umdNm = %s
            AND deal_ymd >= %s AND deal_ymd <= %s
            GROUP BY sggCd, jibun, buildYear
            HAVING COUNT(*) >= 2
        )
        AND deal_ymd >= %s AND deal_ymd <= %s
        ORDER BY sggCd, jibun, buildYear, deal_ymd;
        """
        query_params = (district_name, district_name, start_ymd, target_ymd, start_ymd, target_ymd)

        connection = self._get_db_connection()
        if not connection:
            return pd.DataFrame()

        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, query_params)
                rows = cursor.fetchall()
            df = pd.DataFrame(rows)
            if df.empty:
                print(f"{district_name} {floor_type} 분석 기간 내 2회 이상 거래된 건물이 없습니다.")
                return pd.DataFrame()

            df["floor_type"] = floor_type
            print(f"{district_name} {floor_type} 총 {df.groupby(['sggCd', 'jibun', 'buildYear']).ngroups}개 건물의 데이터를 분석합니다...")

            df_sorted = df.sort_values(by="deal_ymd")
            grouped = df_sorted.groupby(["sggCd", "jibun", "buildYear"], group_keys=False)
            try:
                results_df = grouped.apply(calculate_surge_score, include_groups=False)
            except TypeError:
                results_df = grouped.apply(calculate_surge_score)
            results_df.dropna(subset=["sggCd"], inplace=True)
            return results_df
        except Error as e:
            print(f"데이터 조회 중 오류 발생: {e}")
            return pd.DataFrame()
        finally:
            if connection.is_connected():
                connection.close()

    def find_surging_properties(self, target_ymd, district_name, top_n=10, analysis_period_months=6):
        end_date = datetime.strptime(target_ymd, "%Y%m")
        start_date = end_date - relativedelta(months=analysis_period_months - 1)
        start_ymd = start_date.strftime("%Y%m")

        print(f"분석 기간: {start_ymd} ~ {target_ymd} (총 {analysis_period_months}개월)")
        print(f"분석 대상 지역: {district_name}")
        print("지상층과 지하층 데이터를 모두 분석합니다.")

        above_ground_results = self._get_data_from_table(
            "building_transaction_analysis_above_ground",
            start_ymd,
            target_ymd,
            "지상",
            district_name,
        )
        below_ground_results = self._get_data_from_table(
            "building_transaction_analysis_below_ground",
            start_ymd,
            target_ymd,
            "지하",
            district_name,
        )

        combined_results = pd.concat([above_ground_results, below_ground_results])
        if combined_results.empty:
            print(f"{district_name} 분석 기간 내 급등 신호가 포착된 건물이 없습니다.")
            return pd.DataFrame()

        combined_results = combined_results[combined_results["surge_score"] >= 0]
        if combined_results.empty:
            print(f"{district_name} 분석 기간 내 양수 급등 신호가 포착된 건물이 없습니다.")
            return pd.DataFrame()

        combined_results = combined_results.sort_values(by="surge_score", ascending=False).reset_index(drop=True)
        num_to_return = min(top_n, len(combined_results))

        top_results = combined_results.head(num_to_return).copy()
        top_results["rank"] = np.arange(1, len(top_results) + 1)

        final_columns = [
            "rank",
            "sggCd",
            "umdNm",
            "jibun",
            "buildYear",
            "mhouseNm",
            "surge_score",
            "reliability_score",
            "latest_trade_ymd",
            "avg_dealAmount",
            "floor_type",
        ]
        return top_results[final_columns]
