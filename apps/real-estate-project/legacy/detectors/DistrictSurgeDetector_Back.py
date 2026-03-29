import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np


class DistrictSurgeDetector:
    """
    확정된 로직에 따라 과거 특정 시점의 급등 건물을 탐지하고 순위를 매기는 클래스.
    지상층(1층 이상)과 지하층(-1층 이하) 데이터를 모두 분석하여 결과를 통합합니다.
    특정 동(district)에 대한 분석만 수행하고 상위 N개 결과를 반환합니다.
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
        if exclu_first_price is not None and exclu_first_price > 0:
            exclu_cumulative_return = ((exclu_last_price - exclu_first_price) / exclu_first_price) * 100
        else:
            exclu_cumulative_return = 0

        # 대지권 기준 누적 수익률
        land_first_price = first_row['avg_land_price_per_pyeong']
        land_last_price = last_row['avg_land_price_per_pyeong']
        if land_first_price is not None and land_first_price > 0:
            land_cumulative_return = ((land_last_price - land_first_price) / land_first_price) * 100
        else:
            land_cumulative_return = 0

        cumulative_return = max(exclu_cumulative_return or 0, land_cumulative_return or 0)

        # --- 2. '순간 폭등률' 계산 ---
        # 분석 기간의 첫 거래 데이터는 제외하고, 그 이후의 변동률만으로 계산
        sub_group = group.iloc[1:]

        if not sub_group.empty:
            # 남은 기간 동안의 전용면적/대지권 변동률 중 가장 큰 값
            max_rate = sub_group[['exclu_price_change_rate_vs_prev', 'land_price_change_rate_vs_prev']].max().max()
            max_rate = max_rate if pd.notna(max_rate) else 0
        else:
            max_rate = 0  # 비교 대상이 없으면 0

        surge_score = cumulative_return
        surge_type = '꾸준한 상승률'

        # 신뢰도 지표 (분석 기간 내 총 거래 건수)
        reliability_score = group['trade_count'].sum()

        # 반환 데이터에 avg_dealAmount 추가
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
            'avg_dealAmount': last_row['avg_dealAmount'],
            'floor_type': group['floor_type'].iloc[0]  # 층 유형 정보 유지
        })

    def _get_data_from_table(self, table_name, start_ymd, target_ymd, floor_type, district_name):
        """지정된 테이블에서 특정 동에 대한 데이터를 가져와 분석합니다."""

        # 필요한 모든 컬럼을 명시적으로 SELECT 하도록 변경
        # 특정 동(district_name)에 대한 필터 추가
        query = f"""
        SELECT 
            sggCd, umdNm, jibun, buildYear, mhouseNm, deal_ymd, 
            trade_count, avg_dealAmount,
            avg_exclu_price_per_pyeong, exclu_price_change_rate_vs_prev,
            avg_land_price_per_pyeong, land_price_change_rate_vs_prev
        FROM {table_name}
        WHERE umdNm = '{district_name}'
        AND (sggCd, jibun, buildYear) IN (
            SELECT sggCd, jibun, buildYear
            FROM {table_name}
            WHERE umdNm = '{district_name}'
            AND deal_ymd >= '{start_ymd}' AND deal_ymd <= '{target_ymd}'
            GROUP BY sggCd, jibun, buildYear
            HAVING COUNT(*) >= 2
        )
        AND deal_ymd >= '{start_ymd}' AND deal_ymd <= '{target_ymd}'  -- 분석 기간 제한 추가
        ORDER BY sggCd, jibun, buildYear, deal_ymd;
        """

        connection = self._get_db_connection()
        if not connection:
            return pd.DataFrame()

        try:
            # pandas의 read_sql 사용 시 경고가 발생할 수 있으나, 동작에는 문제가 없습니다.
            df = pd.read_sql(query, connection)
            if df.empty:
                print(f"{district_name} {floor_type} 분석 기간 내 2회 이상 거래된 건물이 없습니다.")
                return pd.DataFrame()

            # 층 유형 정보 추가
            df['floor_type'] = floor_type

            print(
                f"{district_name} {floor_type} 총 {df.groupby(['sggCd', 'jibun', 'buildYear']).ngroups}개 건물의 데이터를 분석합니다...")

            # DataFrame을 미리 시간순으로 정렬
            df_sorted = df.sort_values(by='deal_ymd')

            results_df = df_sorted.groupby(['sggCd', 'jibun', 'buildYear']).apply(self._calculate_surge_score)

            # apply 결과가 None인 경우(거래건수 부족) drop
            results_df.dropna(subset=['sggCd'], inplace=True)

            return results_df

        except Error as e:
            print(f"데이터 조회 중 오류 발생: {e}")
            return pd.DataFrame()
        finally:
            if connection.is_connected():
                connection.close()

    def find_surging_properties(self, target_ymd, district_name, top_n=10, analysis_period_months=6):
        """
        지정된 년월과 기간을 기준으로 특정 동(district)의 지상층과 지하층 데이터를 모두 분석하여
        급등한 건물을 찾아 상위 N개를 반환합니다.

        Parameters:
        -----------
        target_ymd : str
            분석 기준 년월 (예: '202507')
        district_name : str
            분석 대상 동 이름 (예: '송파동')
        top_n : int, optional
            상위 몇 개를 반환할지 지정. 기본값은 10개
        analysis_period_months : int, optional
            분석 기간(개월). 기본값은 6개월
        """

        end_date = datetime.strptime(target_ymd, '%Y%m')
        start_date = end_date - relativedelta(months=analysis_period_months - 1)
        start_ymd = start_date.strftime('%Y%m')

        print(f"분석 기간: {start_ymd} ~ {target_ymd} (총 {analysis_period_months}개월)")
        print(f"분석 대상 지역: {district_name}")
        print("지상층과 지하층 데이터를 모두 분석합니다.")

        # 지상층 데이터 분석
        above_ground_results = self._get_data_from_table(
            'building_transaction_analysis_above_ground',
            start_ymd,
            target_ymd,
            '지상',
            district_name
        )

        # 지하층 데이터 분석
        below_ground_results = self._get_data_from_table(
            'building_transaction_analysis_below_ground',
            start_ymd,
            target_ymd,
            '지하',
            district_name
        )

        # 두 결과 합치기
        combined_results = pd.concat([above_ground_results, below_ground_results])

        if combined_results.empty:
            print(f"{district_name} 분석 기간 내 급등 신호가 포착된 건물이 없습니다.")
            return pd.DataFrame()

        # 급등 점수 기준으로 정렬
        combined_results = combined_results.sort_values(by='surge_score', ascending=False).reset_index(drop=True)

        # 상위 N개 선택 (전체 결과 수보다 많은 경우 전체 반환)
        total_count = len(combined_results)
        num_to_return = min(top_n, total_count)

        top_results = combined_results.head(num_to_return)
        top_results['rank'] = np.arange(1, len(top_results) + 1)

        # 최종 컬럼 목록
        final_columns = [
            'rank', 'sggCd', 'umdNm', 'jibun', 'buildYear', 'mhouseNm',
            'surge_score', 'reliability_score', 'latest_trade_ymd',
            'avg_dealAmount', 'floor_type'
        ]

        return top_results[final_columns]


if __name__ == '__main__':
    from project_config import get_db_config
    # --- 설정 ---
    DB_CONNECTION_INFO = get_db_config()

    detector = DistrictSurgeDetector(db_config=DB_CONNECTION_INFO)

    # --- 백테스팅 실행 ---
    # 분석 기준 년월, 분석 기간(개월)을 설정
    target_analysis_ymd = '202507'
    target_analysis_period_months = 12

    # 사용자 입력으로 동 이름과 상위 개수 입력 받기
    district_name = input("분석할 동 이름을 입력하세요 (예: 송파동): ")

    try:
        top_n = int(input("상위 몇 개의 결과를 보시겠습니까? (기본값: 10): ") or "10")
    except ValueError:
        print("유효한 숫자가 아닙니다. 기본값 10을 사용합니다.")
        top_n = 10

    print(
        f"\n--- 급등 신호 백테스팅 시작 (기준: {target_analysis_ymd}, 지역: {district_name}, 상위: {top_n}개, 기간: {target_analysis_period_months}개월) ---")

    surging_properties = detector.find_surging_properties(
        target_ymd=target_analysis_ymd,
        district_name=district_name,
        top_n=top_n,
        analysis_period_months=target_analysis_period_months
    )

    if not surging_properties.empty:
        print("\n[백테스팅 결과: 급등 신호 포착 목록]")
        print(surging_properties.to_string())
    else:
        print("\n[백테스팅 결과: 포착된 급등 신호가 없습니다.]")