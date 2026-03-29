import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
from map_drawing import map_utils
import math
import os


class ClusterSurgeDetector:
    """
    확정된 로직에 따라 과거 특정 시점의 급등 건물을 탐지하고 순위를 매기는 클래스.
    지상층(1층 이상)과 지하층(-1층 이하) 데이터를 모두 분석하여 결과를 통합합니다.
    각 건물을 중심으로 지정된 거리 범위 내의 건물들을 클러스터링하여
    평균 급등 점수가 가장 높은 지역을 찾습니다.
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

    def get_bounding_box(self, latitude, longitude, distance_in_meters):
        """
        주어진 좌표를 중심으로 지정된 거리(미터)에 해당하는 위경도 범위를 계산합니다.

        Parameters:
        -----------
        latitude : float
            중심 좌표의 위도
        longitude : float
            중심 좌표의 경도
        distance_in_meters : float
            거리(미터)

        Returns:
        --------
        tuple
            (min_lat, max_lat, min_lon, max_lon) 형태의 위경도 범위
        """
        # 지구 반경 (미터)
        earth_radius = 6371000

        # 위도 1도의 미터 거리 (대략적인 값)
        meters_per_lat = 111320

        # 경도 1도의 미터 거리 (위도에 따라 달라짐)
        meters_per_lon = 111320 * math.cos(math.radians(latitude))

        # 위도 범위 계산
        lat_delta = distance_in_meters / meters_per_lat
        min_lat = latitude - lat_delta
        max_lat = latitude + lat_delta

        # 경도 범위 계산
        lon_delta = distance_in_meters / meters_per_lon
        min_lon = longitude - lon_delta
        max_lon = longitude + lon_delta

        return min_lat, max_lat, min_lon, max_lon

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

        # 변경된 로직
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

    def _get_data_from_table(self, table_name, start_ymd, target_ymd, floor_type):
        """지정된 테이블에서 데이터를 가져와 분석합니다."""

        # 필요한 모든 컬럼을 명시적으로 SELECT 하도록 변경
        query = f"""
        SELECT 
            sggCd, umdNm, jibun, buildYear, mhouseNm, deal_ymd, 
            trade_count, avg_dealAmount,
            avg_exclu_price_per_pyeong, exclu_price_change_rate_vs_prev,
            avg_land_price_per_pyeong, land_price_change_rate_vs_prev
        FROM {table_name}
        WHERE (sggCd, jibun, buildYear) IN (
            SELECT sggCd, jibun, buildYear
            FROM {table_name}
            WHERE deal_ymd >= '{start_ymd}' AND deal_ymd <= '{target_ymd}'
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
                print(f"{floor_type} 분석 기간 내 2회 이상 거래된 건물이 없습니다.")
                return pd.DataFrame()

            # 층 유형 정보 추가
            df['floor_type'] = floor_type

            print(f"{floor_type} 총 {df.groupby(['sggCd', 'jibun', 'buildYear']).ngroups}개 건물의 데이터를 분석합니다...")

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

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        두 지점 간의 거리를 계산합니다 (하버사인 공식 사용).
        결과는 미터 단위입니다.
        """
        # 지구 반경 (미터)
        R = 6371000

        # 라디안으로 변환
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # 위도, 경도 차이
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # 하버사인 공식
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return distance

    def _find_properties_in_range(self, center_lat, center_lon, all_properties, range_meters):
        """
        중심 좌표로부터 지정된 거리 내에 있는 모든 건물을 찾습니다.
        위경도 범위 필터링을 먼저 적용하여 성능을 개선합니다.
        """
        # 위경도 범위 계산
        min_lat, max_lat, min_lon, max_lon = self.get_bounding_box(center_lat, center_lon, range_meters)

        # 위경도 범위로 1차 필터링
        filtered_properties = all_properties[
            (all_properties['latitude'] >= min_lat) &
            (all_properties['latitude'] <= max_lat) &
            (all_properties['longitude'] >= min_lon) &
            (all_properties['longitude'] <= max_lon)
            ]

        # 필터링된 결과에 대해서만 정확한 거리 계산 (선택적)
        properties_in_range = []

        for _, prop in filtered_properties.iterrows():
            if pd.isna(prop['latitude']) or pd.isna(prop['longitude']):
                continue

            # 정확한 거리 계산 (선택적)
            distance = self._calculate_distance(
                center_lat, center_lon,
                prop['latitude'], prop['longitude']
            )

            if distance <= range_meters:
                properties_in_range.append(prop)

        return pd.DataFrame(properties_in_range) if properties_in_range else pd.DataFrame()

    def find_best_cluster(self, target_ymd, range_meters=500, analysis_period_months=6):
        """
        지정된 년월과 기간을 기준으로 지상층과 지하층 데이터를 모두 분석하여
        지정된 거리 범위 내에서 평균 급등 점수가 가장 높은 클러스터를 찾습니다.

        Parameters:
        -----------
        target_ymd : str
            분석 기준 년월 (예: '202507')
        range_meters : int, optional
            클러스터링할 거리 범위(미터). 기본값은 500미터
        analysis_period_months : int, optional
            분석 기간(개월). 기본값은 6개월
        """

        end_date = datetime.strptime(target_ymd, '%Y%m')
        start_date = end_date - relativedelta(months=analysis_period_months - 1)
        start_ymd = start_date.strftime('%Y%m')

        print(f"분석 기간: {start_ymd} ~ {target_ymd} (총 {analysis_period_months}개월)")
        print(f"클러스터링 거리 범위: {range_meters}미터")
        print("지상층과 지하층 데이터를 모두 분석합니다.")

        # 지상층 데이터 분석
        above_ground_results = self._get_data_from_table(
            'building_transaction_analysis_above_ground',
            start_ymd,
            target_ymd,
            '지상'
        )

        # 지하층 데이터 분석
        below_ground_results = self._get_data_from_table(
            'building_transaction_analysis_below_ground',
            start_ymd,
            target_ymd,
            '지하'
        )

        # 두 결과 합치기
        combined_results = pd.concat([above_ground_results, below_ground_results])

        # surge_score가 0 이상인 행만 필터링 (음수 제외)
        combined_results = combined_results[combined_results['surge_score'] >= 0]

        if combined_results.empty:
            print("분석 기간 내 급등 신호가 포착된 건물이 없습니다.")
            return None

        # 각 건물에 고유 ID 부여
        combined_results['id'] = np.arange(len(combined_results))

        # 주소 변환 및 좌표 추출
        print("\n주소 변환 및 좌표 추출 중...")
        addresses = []
        latitudes = []
        longitudes = []

        for _, row in combined_results.iterrows():
            address = map_utils.build_address_from_code(
                row['sggCd'],
                row['umdNm'],
                row['jibun']
            )

            if address:
                lat, lon = map_utils.get_kakao_coords(address)
                addresses.append(address)
                latitudes.append(lat)
                longitudes.append(lon)
            else:
                addresses.append(None)
                latitudes.append(None)
                longitudes.append(None)

        combined_results['address'] = addresses
        combined_results['latitude'] = latitudes
        combined_results['longitude'] = longitudes

        # 좌표가 없는 행 제거
        valid_results = combined_results.dropna(subset=['latitude', 'longitude'])

        if valid_results.empty:
            print("유효한 좌표를 가진 건물이 없습니다.")
            return None

        print(f"총 {len(valid_results)}개 건물의 좌표를 추출했습니다.")

        # 각 건물을 중심으로 클러스터 분석
        print("\n클러스터 분석 중...")
        best_cluster = None
        best_avg_score = -float('inf')

        for idx, center_prop in valid_results.iterrows():
            cluster = self._find_properties_in_range(
                center_prop['latitude'],
                center_prop['longitude'],
                valid_results,
                range_meters
            )

            if not cluster.empty:
                avg_score = cluster['surge_score'].mean()

                if avg_score > best_avg_score:
                    best_avg_score = avg_score

                    # 클러스터 정보 저장
                    best_cluster = {
                        'center_id': center_prop['id'],
                        'avg_surge_score': avg_score,
                        'properties': cluster,
                        'coordinates': [(row['latitude'], row['longitude']) for _, row in cluster.iterrows()],
                        'surge_scores': cluster['surge_score'].tolist(),
                        'addresses': [row['address'] for _, row in cluster.iterrows()]
                    }

        if best_cluster:
            print(f"\n최적 클러스터 발견: 평균 급등 점수 {best_cluster['avg_surge_score']:.2f}%")
            print(f"클러스터 내 건물 수: {len(best_cluster['properties'])}")

            # 지도 생성
            output_dir = "/Users/hank.es/LocalBigqueryTask/RealEstateProject/map_images"
            output_filename = f"상위지역_{range_meters}미터_{target_ymd}_{analysis_period_months}months.html"

            print(f"\n지도 생성 중... ({output_filename})")
            map_utils.create_map_with_multiple_addresses(
                address_list=best_cluster['addresses'],
                value_list=best_cluster['surge_scores'],
                output_dir=output_dir,
                output_filename=output_filename
            )

            return best_cluster
        else:
            print("클러스터 분석 결과가 없습니다.")
            return None


if __name__ == '__main__':
    from project_config import get_db_config
    # --- 설정 ---
    DB_CONNECTION_INFO = get_db_config()

    detector = ClusterSurgeDetector(db_config=DB_CONNECTION_INFO)

    # --- 백테스팅 실행 ---
    # 분석 기준 년월, 분석 기간(개월)을 설정
    target_analysis_ymd = '202507'
    target_analysis_period_months = 6

    # 사용자 입력으로 클러스터링 거리 범위 입력 받기
    try:
        cluster_range_meters = int(input("클러스터링 거리 범위(미터)를 입력하세요 (기본값: 500): ") or "500")
    except ValueError:
        print("유효한 숫자가 아닙니다. 기본값 500을 사용합니다.")
        cluster_range_meters = 500

    print(
        f"\n--- 급등 클러스터 분석 시작 (기준: {target_analysis_ymd}, 거리범위: {cluster_range_meters}m, 기간: {target_analysis_period_months}개월) ---")

    best_cluster = detector.find_best_cluster(
        target_ymd=target_analysis_ymd,
        range_meters=cluster_range_meters,
        analysis_period_months=target_analysis_period_months
    )

    if best_cluster:
        print("\n[분석 결과: 최적 급등 클러스터 발견]")
        print(f"평균 급등 점수: {best_cluster['avg_surge_score']:.2f}%")
        print(f"클러스터 내 건물 수: {len(best_cluster['properties'])}")
        print("\n클러스터 내 건물 목록:")
        print(best_cluster['properties'][['rank', 'sggCd', 'umdNm', 'jibun', 'buildYear', 'mhouseNm', 'surge_score',
                                          'floor_type']].to_string())
    else:
        print("\n[분석 결과: 급등 클러스터를 찾을 수 없습니다.]")