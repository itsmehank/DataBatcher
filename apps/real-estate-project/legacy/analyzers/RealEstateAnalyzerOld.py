import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta


class RealEstateAnalyzer:
    """
    rh_trade_analysis 테이블의 원본 데이터를 바탕으로,
    동(umdNm)과 년월(deal_ymd) 단위의 2차 분석 데이터를 생성하고
    별도의 요약 테이블에 저장하는 클래스.
    """

    def __init__(self, db_config):
        """
        클래스 초기화.
        :param db_config: MySQL 연결 정보 (딕셔너리 형태).
        """
        self.db_config = db_config
        # 데이터 갱신 주기를 설정 (현재 월, 지난달)
        now = datetime.now()
        self.latest_months = [
            now.strftime('%Y%m'),
            (now - relativedelta(months=1)).strftime('%Y%m')
        ]

    def _get_db_connection(self):
        """데이터베이스 연결을 생성하고 반환합니다. (트랜잭션 관리를 위해 autocommit=False)"""
        try:
            connection = mysql.connector.connect(**self.db_config, autocommit=False)
            return connection
        except Error as e:
            print(f"데이터베이스 연결 중 오류 발생: {e}")
            return None

    def _create_analysis_table(self, connection, table_name):
        """2차 분석 데이터를 저장할 요약 테이블을 생성합니다."""
        query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sggCd VARCHAR(10) NOT NULL,
            umdNm VARCHAR(100) NOT NULL,
            deal_ymd VARCHAR(6) NOT NULL,

            -- 1번 타입: 전체 층 대상
            total_avg_price_per_pyeong DECIMAL(20, 2) COMMENT '전체 평균 평당 단가',
            total_avg_land_price_per_pyeong DECIMAL(20, 2) COMMENT '전체 평균 대지 평당 단가',
            total_trade_count INT COMMENT '전체 거래 건수',
            low_floor_trade_ratio DECIMAL(5, 4) COMMENT '전체 거래 대비 저층(1층 미만) 거래 비율',
            direct_trade_count INT COMMENT '직거래 건수',
            ind_to_corp_trade_count INT COMMENT '개인 매도 & 법인 매수 거래 건수',

            -- 2번 타입: 1층 이상
            high_floor_avg_price_per_pyeong DECIMAL(20, 2) COMMENT '1층 이상 평균 평당 단가',
            high_floor_avg_land_price_per_pyeong DECIMAL(20, 2) COMMENT '1층 이상 평균 대지 평당 단가',
            high_floor_trade_count INT COMMENT '1층 이상 거래 건수',

            -- 3번 타입: 1층 미만 (지하)
            low_floor_avg_price_per_pyeong DECIMAL(20, 2) COMMENT '1층 미만 평균 평당 단가',
            low_floor_avg_land_price_per_pyeong DECIMAL(20, 2) COMMENT '1층 미만 평균 대지 평당 단가',
            low_floor_trade_count INT COMMENT '1층 미만 거래 건수',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_sgg_umd_ymd (sggCd, umdNm, deal_ymd)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='월별 동단위 연립다세대 거래 분석 요약';
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
            connection.commit()
            print(f"2차 분석 테이블 '{table_name}'이(가) 성공적으로 준비되었습니다.")
        except Error as e:
            print(f"2차 분석 테이블 생성 중 오류 발생: {e}")
            connection.rollback()

    def _create_log_table(self, connection):
        """2차 분석 작업 로그를 기록할 테이블을 생성합니다."""
        query = """
                CREATE TABLE IF NOT EXISTS analysis_log_dong \
                ( \
                    id \
                    INT \
                    AUTO_INCREMENT \
                    PRIMARY \
                    KEY, \
                    sggCd \
                    VARCHAR \
                ( \
                    10 \
                ) NOT NULL,
                    umdNm VARCHAR \
                ( \
                    100 \
                ) NOT NULL,
                    deal_ymd VARCHAR \
                ( \
                    6 \
                ) NOT NULL,
                    status VARCHAR \
                ( \
                    20 \
                ) DEFAULT 'SUCCESS',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_sgg_umd_ymd_log \
                ( \
                    sggCd, \
                    umdNm, \
                    deal_ymd \
                ),
                    INDEX idx_sgg_umd \
                ( \
                    sggCd, \
                    umdNm \
                ) COMMENT '분석 조회용 복합 인덱스'
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='동단위 분석 작업 로그'; \
                """
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
            connection.commit()
            print("2차 분석 로그 테이블 'analysis_log_dong'이(가) 성공적으로 준비되었습니다.")
        except Error as e:
            print(f"2차 분석 로그 테이블 생성 중 오류 발생: {e}")
            connection.rollback()

    def setup_database(self, analysis_table_name):
        """분석에 필요한 모든 테이블을 초기 설정합니다."""
        db_info_for_setup = self.db_config.copy()
        db_name = db_info_for_setup.pop('database')

        try:
            with mysql.connector.connect(**db_info_for_setup) as conn_no_db:
                with conn_no_db.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")

            with self._get_db_connection() as connection:
                if connection:
                    self._create_analysis_table(connection, analysis_table_name)
                    self._create_log_table(connection)
        except Error as e:
            print(f"데이터베이스 설정 중 심각한 오류 발생: {e}")

    def _process_analysis_group(self, connection, group_info, source_table, target_table):
        """단일 그룹(sggCd, umdNm, deal_ymd)에 대한 분석 및 적재를 수행합니다."""
        sggCd, umdNm, deal_ymd = group_info

        with connection.cursor() as cursor:
            # 1. 작업 대상인지 확인 (로그 및 최신월 체크)
            is_latest = deal_ymd in self.latest_months
            log_check_query = "SELECT 1 FROM analysis_log_dong WHERE sggCd = %s AND umdNm = %s AND deal_ymd = %s"
            cursor.execute(log_check_query, (sggCd, umdNm, deal_ymd))
            is_logged = cursor.fetchone() is not None

            if not is_latest and is_logged:
                # print(f"[{sggCd}-{umdNm}-{deal_ymd}] 이미 처리된 데이터입니다. 건너뜁니다.")
                return True

            # 2. SQL을 통한 데이터 집계 (분석 기준 변경)
            agg_query = f"""
            SELECT
                -- Type 1: 전체
                AVG(price_per_pyeong),
                AVG(land_price_per_pyeong),
                COUNT(*),
                SUM(CASE WHEN floor < 1 THEN 1 ELSE 0 END),
                SUM(CASE WHEN dealingGbn = '직거래' THEN 1 ELSE 0 END),
                SUM(CASE WHEN slerGbn = '개인' AND buyerGbn = '법인' THEN 1 ELSE 0 END),
                -- Type 2: 1층 이상
                AVG(CASE WHEN floor >= 1 THEN price_per_pyeong ELSE NULL END),
                AVG(CASE WHEN floor >= 1 THEN land_price_per_pyeong ELSE NULL END),
                SUM(CASE WHEN floor >= 1 THEN 1 ELSE 0 END),
                -- Type 3: 1층 미만
                AVG(CASE WHEN floor < 1 THEN price_per_pyeong ELSE NULL END),
                AVG(CASE WHEN floor < 1 THEN land_price_per_pyeong ELSE NULL END)
            FROM {source_table}
            WHERE sggCd = %s AND umdNm = %s AND dealYear = %s AND dealMonth = %s;
            """
            year, month = int(deal_ymd[:4]), int(deal_ymd[4:])
            cursor.execute(agg_query, (sggCd, umdNm, year, month))
            result = cursor.fetchone()

            if not result or result[2] == 0:  # 거래가 없는 경우
                print(f"[{sggCd}-{umdNm}-{deal_ymd}] 분석할 데이터가 없습니다.")
                return True

            # 3. 집계 결과 정리
            total_trade_count = result[2]
            low_floor_count = result[3]
            low_floor_trade_ratio = (low_floor_count / total_trade_count) if total_trade_count > 0 else 0

            analysis_data = {
                'sggCd': sggCd, 'umdNm': umdNm, 'deal_ymd': deal_ymd,
                'total_avg_price_per_pyeong': result[0], 'total_avg_land_price_per_pyeong': result[1],
                'total_trade_count': total_trade_count, 'low_floor_trade_ratio': low_floor_trade_ratio,
                'direct_trade_count': result[4], 'ind_to_corp_trade_count': result[5],
                'high_floor_avg_price_per_pyeong': result[6], 'high_floor_avg_land_price_per_pyeong': result[7],
                'high_floor_trade_count': result[8], 'low_floor_avg_price_per_pyeong': result[9],
                'low_floor_avg_land_price_per_pyeong': result[10], 'low_floor_trade_count': low_floor_count
            }

            # 4. DB 작업 (트랜잭션 내에서 실행)
            try:
                # 4-1. 최신 월 데이터는 기존 분석 데이터 삭제
                if is_latest:
                    delete_query = f"DELETE FROM {target_table} WHERE sggCd = %s AND umdNm = %s AND deal_ymd = %s"
                    cursor.execute(delete_query, (sggCd, umdNm, deal_ymd))

                # 4-2. 신규 분석 데이터 삽입
                insert_query = f"""
                INSERT INTO {target_table} (
                    sggCd, umdNm, deal_ymd, total_avg_price_per_pyeong, total_avg_land_price_per_pyeong,
                    total_trade_count, low_floor_trade_ratio, direct_trade_count, ind_to_corp_trade_count,
                    high_floor_avg_price_per_pyeong, high_floor_avg_land_price_per_pyeong, high_floor_trade_count,
                    low_floor_avg_price_per_pyeong, low_floor_avg_land_price_per_pyeong, low_floor_trade_count
                ) VALUES (
                    %(sggCd)s, %(umdNm)s, %(deal_ymd)s, %(total_avg_price_per_pyeong)s, %(total_avg_land_price_per_pyeong)s,
                    %(total_trade_count)s, %(low_floor_trade_ratio)s, %(direct_trade_count)s, %(ind_to_corp_trade_count)s,
                    %(high_floor_avg_price_per_pyeong)s, %(high_floor_avg_land_price_per_pyeong)s, %(high_floor_trade_count)s,
                    %(low_floor_avg_price_per_pyeong)s, %(low_floor_avg_land_price_per_pyeong)s, %(low_floor_trade_count)s
                )
                """
                cursor.execute(insert_query, analysis_data)

                # 4-3. 작업 성공 로그 기록
                log_insert_query = "INSERT IGNORE INTO analysis_log_dong (sggCd, umdNm, deal_ymd) VALUES (%s, %s, %s)"
                cursor.execute(log_insert_query, (sggCd, umdNm, deal_ymd))
                print(f"[{sggCd}-{umdNm}-{deal_ymd}] 분석 데이터 처리를 완료했습니다.")
                return True
            except Error as e:
                print(f"DB 작업 중 오류 발생 ({sggCd}-{umdNm}-{deal_ymd}): {e}")
                return False

    def run_analysis(self, source_table, target_table):
        """전체 분석 작업을 오케스트레이션합니다."""
        with self._get_db_connection() as connection:
            if not connection:
                print("DB 연결 실패. 작업을 중단합니다.")
                return

            with connection.cursor() as cursor:
                # 처리해야 할 (sggCd, umdNm, deal_ymd) 그룹 목록을 효율적으로 가져옴
                get_groups_query = f"""
                SELECT DISTINCT sggCd, umdNm, CONCAT(dealYear, LPAD(dealMonth, 2, '0')) as deal_ymd
                FROM {source_table}
                ORDER BY sggCd, umdNm, deal_ymd;
                """
                cursor.execute(get_groups_query)
                groups_to_process = cursor.fetchall()

            print(f"총 {len(groups_to_process)}개의 동-월 그룹에 대한 분석을 시작합니다.")

            for group in groups_to_process:
                success = self._process_analysis_group(connection, group, source_table, target_table)
                if success:
                    connection.commit()
                else:
                    connection.rollback()
                    print(f"작업 실패로 인해 {group} 처리를 롤백했습니다.")


if __name__ == '__main__':
    from project_config import get_db_config
    # --- 설정 ---
    DB_CONNECTION_INFO = get_db_config()

    SOURCE_TABLE = 'rh_trade_analysis'
    TARGET_TABLE = 'monthly_dong_analysis'

    # --- 클래스 인스턴스 생성 ---
    analyzer = RealEstateAnalyzer(db_config=DB_CONNECTION_INFO)

    # 1. 2차 분석을 위한 데이터베이스 테이블 준비
    print("--- 1. 2차 분석용 데이터베이스 설정 작업 시작 ---")
    analyzer.setup_database(analysis_table_name=TARGET_TABLE)
    print("--- 2차 분석용 데이터베이스 설정 완료 ---\n")

    # 2. 2차 분석 작업 실행
    print(f"--- 2. '{SOURCE_TABLE}' 테이블을 원본으로 2차 분석 작업 시작 ---")
    analyzer.run_analysis(source_table=SOURCE_TABLE, target_table=TARGET_TABLE)
    print("--- 모든 2차 분석 작업 완료 ---")
