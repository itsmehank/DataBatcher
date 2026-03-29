from datetime import datetime

import mysql.connector
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from mysql.connector import Error


class RealEstateAnalyzer:
    """
    rh_trade_analysis 테이블의 원본 데이터를 바탕으로,
    동(umdNm)과 년월(deal_ymd) 단위의 2차 분석 데이터를 생성하고
    별도의 요약 테이블에 저장하는 클래스.
    시계열 분석 지표를 포함하도록 기능이 확장되었습니다.
    """

    def __init__(self, db_config):
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

    def setup_database(self, analysis_table_name):
        from project_config import ensure_schema
        ensure_schema(self.db_config)

    def _process_dong_group(self, connection, sgg_cd, umd_nm, source_table, target_table):
        query = f"SELECT * FROM {source_table} WHERE sggCd = %s AND umdNm = %s"
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (sgg_cd, umd_nm))
            rows = cursor.fetchall()
        df = pd.DataFrame(rows)
        if df.empty:
            return

        numeric_columns = [
            "price_per_pyeong",
            "land_price_per_pyeong",
            "floor",
            "id",
            "dealYear",
            "dealMonth",
        ]
        for column in numeric_columns:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce")

        df["deal_ymd"] = df["dealYear"].astype(str) + df["dealMonth"].astype(str).str.zfill(2)

        std_df = df.groupby("deal_ymd").agg(price_per_pyeong_stddev=("price_per_pyeong", lambda x: x.std(ddof=0))).reset_index()

        agg_df = df.groupby("deal_ymd").agg(
            total_avg_price_per_pyeong=("price_per_pyeong", "mean"),
            total_avg_land_price_per_pyeong=("land_price_per_pyeong", "mean"),
            total_trade_count=("id", "count"),
            low_floor_count=("floor", lambda x: (x < 1).sum()),
            direct_trade_count=("dealingGbn", lambda x: (x == "직거래").sum()),
            ind_to_corp_trade_count=(
                "id",
                lambda x: ((df.loc[x.index, "slerGbn"] == "개인") & (df.loc[x.index, "buyerGbn"] == "법인")).sum(),
            ),
            high_floor_avg_price_per_pyeong=("price_per_pyeong", lambda x: x[df.loc[x.index, "floor"] >= 1].mean()),
            high_floor_avg_land_price_per_pyeong=(
                "land_price_per_pyeong",
                lambda x: x[df.loc[x.index, "floor"] >= 1].mean(),
            ),
            high_floor_trade_count=("floor", lambda x: (x >= 1).sum()),
            low_floor_avg_price_per_pyeong=("price_per_pyeong", lambda x: x[df.loc[x.index, "floor"] < 1].mean()),
            low_floor_avg_land_price_per_pyeong=(
                "land_price_per_pyeong",
                lambda x: x[df.loc[x.index, "floor"] < 1].mean(),
            ),
        ).reset_index()

        final_df = pd.merge(agg_df, std_df, on="deal_ymd")
        final_df["low_floor_trade_ratio"] = (final_df["low_floor_count"] / final_df["total_trade_count"]).where(
            final_df["total_trade_count"] > 0, 0
        )
        final_df["low_floor_trade_count"] = final_df["low_floor_count"]

        final_df = final_df.sort_values("deal_ymd").reset_index(drop=True)
        final_df["prev_price"] = final_df["total_avg_price_per_pyeong"].shift(1)
        final_df["price_change_rate_vs_prev"] = (
            (final_df["total_avg_price_per_pyeong"] - final_df["prev_price"]) / final_df["prev_price"] * 100
        ).where(final_df["prev_price"] > 0)

        final_df["prev_ymd"] = pd.to_datetime(final_df["deal_ymd"].shift(1), format="%Y%m", errors="coerce")
        current_ymd = pd.to_datetime(final_df["deal_ymd"], format="%Y%m")
        final_df["months_since_prev_trade"] = (current_ymd.dt.year - final_df["prev_ymd"].dt.year) * 12 + (
            current_ymd.dt.month - final_df["prev_ymd"].dt.month
        )

        cumulative_volume = final_df["total_trade_count"].expanding().sum().shift(1)
        cumulative_months = pd.Series(range(len(final_df))).shift(1)
        final_df["avg_monthly_volume_cumulative"] = (cumulative_volume / cumulative_months).where(cumulative_months > 0)
        final_df["volume_change_rate_vs_avg"] = (
            (final_df["total_trade_count"] / final_df["avg_monthly_volume_cumulative"]) * 100
        ).where(final_df["avg_monthly_volume_cumulative"] > 0)

        final_df["is_low_volume"] = final_df["total_trade_count"] < 5
        final_df = final_df.replace({np.nan: None, np.inf: None, -np.inf: None})

        with connection.cursor() as cursor:
            for _, row in final_df.iterrows():
                deal_ymd = row["deal_ymd"]
                is_latest = deal_ymd in self.latest_months
                log_check_query = "SELECT 1 FROM analysis_log_dong WHERE sggCd = %s AND umdNm = %s AND deal_ymd = %s"
                cursor.execute(log_check_query, (sgg_cd, umd_nm, deal_ymd))
                is_logged = cursor.fetchone() is not None

                if not is_latest and is_logged:
                    continue

                try:
                    if is_latest:
                        delete_query = f"DELETE FROM {target_table} WHERE sggCd = %s AND umdNm = %s AND deal_ymd = %s"
                        cursor.execute(delete_query, (sgg_cd, umd_nm, deal_ymd))

                    row_data = row.to_dict()
                    row_data["sggCd"] = sgg_cd
                    row_data["umdNm"] = umd_nm

                    cols = ", ".join(f"`{k}`" for k in row_data.keys() if k in self.analysis_table_columns)
                    vals = ", ".join(f"%({k})s" for k in row_data.keys() if k in self.analysis_table_columns)
                    insert_query = f"INSERT INTO {target_table} ({cols}) VALUES ({vals})"
                    cursor.execute(insert_query, row_data)

                    log_insert_query = "INSERT IGNORE INTO analysis_log_dong (sggCd, umdNm, deal_ymd) VALUES (%s, %s, %s)"
                    cursor.execute(log_insert_query, (sgg_cd, umd_nm, deal_ymd))
                except Error as e:
                    print(f"DB 작업 중 오류 발생 ({sgg_cd}-{umd_nm}-{deal_ymd}): {e}")
                    connection.rollback()
                    return

        connection.commit()
        print(f"[{sgg_cd}-{umd_nm}] 그룹 분석 및 저장을 완료했습니다.")

    def run_analysis(self, source_table, target_table):
        with self._get_db_connection() as connection:
            if not connection:
                print("DB 연결 실패. 작업을 중단합니다.")
                return

            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(f"SHOW COLUMNS FROM {target_table}")
                self.analysis_table_columns = {col["Field"] for col in cursor.fetchall()}

                get_groups_query = f"SELECT DISTINCT sggCd, umdNm FROM {source_table} ORDER BY sggCd, umdNm;"
                cursor.execute(get_groups_query)
                groups_to_process = cursor.fetchall()

            print(f"총 {len(groups_to_process)}개의 동 그룹에 대한 분석을 시작합니다.")

            for group in groups_to_process:
                self._process_dong_group(connection, group["sggCd"], group["umdNm"], source_table, target_table)
