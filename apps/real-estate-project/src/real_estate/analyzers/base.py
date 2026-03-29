from datetime import datetime

import mysql.connector
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from mysql.connector import Error


class BaseBuildingAnalyzer:
    def __init__(
        self,
        db_config,
        *,
        floor_condition=None,
        log_table_name="analysis_log_building",
        table_comment="월별 건물단위(지번+건축년도) 연립다세대 거래 분석",
        log_comment="건물단위(지번+건축년도) 분석 작업 로그",
        analyzer_label="건물",
        avg_deal_column="avg_dealAmount",
        avg_deal_sql_type="BIGINT",
        parse_deal_amount=False,
    ):
        self.db_config = db_config
        self.floor_condition = floor_condition
        self.log_table_name = log_table_name
        self.table_comment = table_comment
        self.log_comment = log_comment
        self.analyzer_label = analyzer_label
        self.avg_deal_column = avg_deal_column
        self.avg_deal_sql_type = avg_deal_sql_type
        self.parse_deal_amount = parse_deal_amount

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

    def _get_floor_where_clause(self):
        if not self.floor_condition:
            return ""
        return f" AND {self.floor_condition}"

    def setup_database(self, analysis_table_name):
        from project_config import ensure_schema
        ensure_schema(self.db_config)

    def _process_building_group(self, connection, sgg_cd, jibun, build_year, source_table, target_table):
        group_key_log = f"[{sgg_cd}-{jibun}-{build_year}]"
        floor_clause = self._get_floor_where_clause()

        with connection.cursor() as cursor:
            check_latest_query = f"""
            SELECT 1 FROM {source_table}
            WHERE sggCd = %s AND jibun = %s AND buildYear = %s{floor_clause}
            AND CONCAT(dealYear, LPAD(dealMonth, 2, '0')) IN ({','.join(['%s'] * len(self.latest_months))})
            LIMIT 1;
            """
            params = [sgg_cd, jibun, build_year] + self.latest_months
            cursor.execute(check_latest_query, params)
            needs_reprocessing = cursor.fetchone() is not None

            log_check_query = f"SELECT 1 FROM {self.log_table_name} WHERE sggCd = %s AND jibun = %s AND buildYear = %s"
            cursor.execute(log_check_query, (sgg_cd, jibun, build_year))
            is_logged = cursor.fetchone() is not None

            if is_logged and not needs_reprocessing:
                return True

        query = f"""
        SELECT dealYear, dealMonth, price_per_pyeong, land_price_per_pyeong, umdNm, mhouseNm, dealAmount, id
        FROM {source_table}
        WHERE sggCd = %s AND jibun = %s AND buildYear = %s{floor_clause}
        """
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, [sgg_cd, jibun, build_year])
            rows = cursor.fetchall()
        df = pd.DataFrame(rows)
        if df.empty:
            return True

        if self.parse_deal_amount:
            df["dealAmount"] = pd.to_numeric(df["dealAmount"].astype(str).str.replace(",", ""), errors="coerce")

        df["deal_ymd"] = df["dealYear"].astype(str) + df["dealMonth"].astype(str).str.zfill(2)
        monthly_df = df.groupby("deal_ymd").agg(
            avg_exclu_price_per_pyeong=("price_per_pyeong", "mean"),
            avg_land_price_per_pyeong=("land_price_per_pyeong", "mean"),
            trade_count=("id", "count"),
            **{self.avg_deal_column: ("dealAmount", "mean")},
        ).reset_index()

        monthly_df = monthly_df.sort_values("deal_ymd").reset_index(drop=True)
        monthly_df["prev_avg_exclu_price_per_pyeong"] = monthly_df["avg_exclu_price_per_pyeong"].shift(1)
        monthly_df["exclu_price_change_rate_vs_prev"] = (
            (monthly_df["avg_exclu_price_per_pyeong"] - monthly_df["prev_avg_exclu_price_per_pyeong"])
            / monthly_df["prev_avg_exclu_price_per_pyeong"]
            * 100
        ).where(monthly_df["prev_avg_exclu_price_per_pyeong"] > 0)

        monthly_df["prev_avg_land_price_per_pyeong"] = monthly_df["avg_land_price_per_pyeong"].shift(1)
        monthly_df["land_price_change_rate_vs_prev"] = (
            (monthly_df["avg_land_price_per_pyeong"] - monthly_df["prev_avg_land_price_per_pyeong"])
            / monthly_df["prev_avg_land_price_per_pyeong"]
            * 100
        ).where(monthly_df["prev_avg_land_price_per_pyeong"] > 0)

        prev_ymd = pd.to_datetime(monthly_df["deal_ymd"].shift(1), format="%Y%m", errors="coerce")
        current_ymd = pd.to_datetime(monthly_df["deal_ymd"], format="%Y%m")
        monthly_df["months_since_prev_trade"] = (current_ymd.dt.year - prev_ymd.dt.year) * 12 + (
            current_ymd.dt.month - prev_ymd.dt.month
        )

        representative_row = df.iloc[0]
        monthly_df["sggCd"] = sgg_cd
        monthly_df["umdNm"] = representative_row["umdNm"]
        monthly_df["jibun"] = jibun
        monthly_df["buildYear"] = build_year
        monthly_df["mhouseNm"] = representative_row["mhouseNm"]

        monthly_df = monthly_df.replace({np.nan: None, np.inf: None, -np.inf: None})

        try:
            with connection.cursor() as cursor:
                delete_query = f"DELETE FROM {target_table} WHERE sggCd = %s AND jibun = %s AND buildYear = %s"
                cursor.execute(delete_query, (sgg_cd, jibun, build_year))

                cols = [
                    "sggCd",
                    "umdNm",
                    "jibun",
                    "buildYear",
                    "mhouseNm",
                    "deal_ymd",
                    "trade_count",
                    self.avg_deal_column,
                    "avg_exclu_price_per_pyeong",
                    "prev_avg_exclu_price_per_pyeong",
                    "exclu_price_change_rate_vs_prev",
                    "avg_land_price_per_pyeong",
                    "prev_avg_land_price_per_pyeong",
                    "land_price_change_rate_vs_prev",
                    "months_since_prev_trade",
                ]
                insert_query = f"INSERT INTO {target_table} ({', '.join(f'`{c}`' for c in cols)}) VALUES ({', '.join(['%s'] * len(cols))})"
                cursor.executemany(insert_query, monthly_df[cols].to_records(index=False).tolist())

                log_insert_query = f"INSERT INTO {self.log_table_name} (sggCd, jibun, buildYear) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE last_processed_at = CURRENT_TIMESTAMP"
                cursor.execute(log_insert_query, (sgg_cd, jibun, build_year))

            connection.commit()
            print(f"{group_key_log} {self.analyzer_label} 건물 그룹 분석 및 저장을 완료했습니다.")
            return True
        except Error as e:
            print(f"DB 작업 중 오류 발생 {group_key_log}: {e}")
            connection.rollback()
            return False

    def run_analysis(self, source_table, target_table):
        with self._get_db_connection() as connection:
            if not connection:
                print("DB 연결 실패. 작업을 중단합니다.")
                return

            floor_clause = self._get_floor_where_clause()
            where_clause = f" WHERE {self.floor_condition}" if self.floor_condition else ""
            with connection.cursor(dictionary=True) as cursor:
                get_groups_query = (
                    f"SELECT DISTINCT sggCd, jibun, buildYear FROM {source_table}{where_clause} "
                    "ORDER BY sggCd, jibun, buildYear;"
                )
                cursor.execute(get_groups_query)
                groups_to_process = cursor.fetchall()

            print(f"총 {len(groups_to_process)}개의 {self.analyzer_label} 건물(지번+건축년도) 그룹에 대한 분석을 시작합니다.")

            for group in groups_to_process:
                self._process_building_group(
                    connection,
                    group["sggCd"],
                    group["jibun"],
                    group["buildYear"],
                    source_table,
                    target_table,
                )
