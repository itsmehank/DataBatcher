import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np


class SurgeDetector:
    """
    확정된 로직에 따라 과거 특정 시점의 급등 건물을 탐지하고 순위를 매기는 클래스.
    """

    def __init__(self, db_config):
        self.db_config = db_config

    def _get_db_connection(self):
        """데이터베이스 연결을 생성하고 반환합니다."""
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as e:
            print(f"데이터베이스 연결 중 오류 발생: {e}")
            return None

    def _calculate_surge_score(self, group):
        """단일 건물 그룹에 대한 급등 점수와 관련 지표를 계산합니다."""

        # 분석 기간 내 거래가 2건 이상인 경우에만 의미가 있음
        if len(group) < 2:
            return None

        # --- 1. '꾸준한 상승률' 계산 ---
        # 기간 내 첫 거래와 마지막 거래의 가격을 직접 비교
        first_row = group.iloc[0]
        last_row = group.iloc[-1]

        # 전용면적 기준 누적 수익률
        exclu_first_price = first_row['avg_exclu_price_per_pyeong']
        exclu_last_price = last_row['avg_exclu_price_per_pyeong']
        if exclu_first_price > 0:
            exclu_cumulative_return = ((exclu_last_price - exclu_first_price) / exclu_first_price) * 100
        else:
            exclu_cumulative_return = 0

        # 대지권 기준 누적 수익률
        land_first_price = first_row['avg_land_price_per_pyeong']
        land_last_price = last_row['avg_land_price_per_pyeong']
        if land_first_price > 0:
            land_cumulative_return = ((land_last_price - land_first_price) / land_first_price) * 100
        else:
            land_cumulative_return = 0

        cumulative_return = max(exclu_cumulative_return, land_cumulative_return)

        # --- 2. '순간 폭등률' 계산 ---
        # 분석 기간의 첫 거래 데이터는 제외하고, 그 이후의 변동률만으로 계산
        sub_group = group.iloc[1:]

        if not sub_group.empty:
            # 남은 기간 동안의 전용면적/대지권 변동률 중 가장 큰 값
            max_rate = sub_group[['exclu_price_change_rate_vs_prev', 'land_price_change_rate_vs_prev']].max().max()
        else:
            max_rate = 0  # 비교 대상이 없으면 0

        # --- 3. 최종 급등 점수 및 유형 결정 ---
        if max_rate > cumulative_return:
            surge_score = max_rate
            surge_type = '순간 폭등률'
        else:
            surge_score = cumulative_return
            surge_type = '꾸준한 상승률'

        # 신뢰도 지표 (분석 기간 내 총 거래 건수)
        reliability_score = group['trade_count'].sum()

        return pd.Series({
            'sggCd': last_row['sggCd'],
            'umdNm': last_row['umdNm'],
            'jibun': last_row['jibun'],
            'buildYear': last_row['buildYear'],
            'mhouseNm': last_row['mhouseNm'],
            'surge_score': surge_score,
            'surge_type': surge_type,
            'reliability_score': reliability_score,
            'latest_trade_ymd': last_row['deal_ymd'],
        })

    def find_surging_properties(self, target_ymd, top_percent=1.0, analysis_period_months=6):
        """
        지정된 년월과 기간을 기준으로 급등한 건물을 찾아 상위 N%를 반환합니다.
        """

        end_date = datetime.strptime(target_ymd, '%Y%m')
        start_date = end_date - relativedelta(months=analysis_period_months - 1)
        start_ymd = start_date.strftime('%Y%m')

        query = f"""
        SELECT * FROM building_transaction_analysis
        WHERE (sggCd, jibun, buildYear) IN (
            SELECT sggCd, jibun, buildYear
            FROM building_transaction_analysis
            WHERE deal_ymd >= '{start_ymd}' AND deal_ymd <= '{target_ymd}'
            GROUP BY sggCd, jibun, buildYear
            HAVING COUNT(*) >= 2
        )
        ORDER BY sggCd, jibun, buildYear, deal_ymd;
        """

        print(f"분석 기간: {start_ymd} ~ {target_ymd} (총 {analysis_period_months}개월)")

        connection = self._get_db_connection()
        if not connection:
            return pd.DataFrame()

        try:
            df = pd.read_sql(query, connection)
            if df.empty:
                print("분석 기간 내 2회 이상 거래된 건물이 없습니다.")
                return pd.DataFrame()
        except Error as e:
            print(f"데이터 조회 중 오류 발생: {e}")
            return pd.DataFrame()
        finally:
            if connection.is_connected():
                connection.close()

        print(
            f"총 {df['sggCd'].nunique()}개 지역, {df.groupby(['sggCd', 'jibun', 'buildYear']).ngroups}개 건물의 데이터를 분석합니다...")

        # DataFrame을 미리 시간순으로 정렬
        df_sorted = df.sort_values(by='deal_ymd')

        results_df = df_sorted.groupby(['sggCd', 'jibun', 'buildYear']).apply(self._calculate_surge_score).reset_index(
            drop=True)
        results_df = results_df.sort_values(by='surge_score', ascending=False).reset_index(drop=True)

        num_to_return = int(len(results_df) * (top_percent / 100))
        if num_to_return == 0 and len(results_df) > 0:
            num_to_return = 1

        top_results = results_df.head(num_to_return)
        top_results['rank'] = np.arange(1, len(top_results) + 1)

        final_columns = [
            'rank', 'sggCd', 'umdNm', 'jibun', 'buildYear', 'mhouseNm',
            'surge_score', 'surge_type', 'reliability_score', 'latest_trade_ymd'
        ]
        return top_results[final_columns]


if __name__ == '__main__':
    from project_config import get_db_config
    # --- 설정 ---
    DB_CONNECTION_INFO = get_db_config()

    detector = SurgeDetector(db_config=DB_CONNECTION_INFO)

    # --- 백테스팅 실행 ---
    # 분석 기준 년월, 상위 퍼센트, 분석 기간(개월)을 설정
    target_analysis_ymd = '202507'
    target_top_percent = 1.0
    target_analysis_period_months = 12

    print(
        f"\n--- 급등 신호 백테스팅 시작 (기준: {target_analysis_ymd}, 상위: {target_top_percent}%, 기간: {target_analysis_period_months}개월) ---")

    surging_properties = detector.find_surging_properties(
        target_ymd=target_analysis_ymd,
        top_percent=target_top_percent,
        analysis_period_months=target_analysis_period_months
    )

    if not surging_properties.empty:
        print("\n[백테스팅 결과: 급등 신호 포착 목록]")
        print(surging_properties.to_string())
    else:
        print("\n[백테스팅 결과: 포착된 급등 신호가 없습니다.]")
