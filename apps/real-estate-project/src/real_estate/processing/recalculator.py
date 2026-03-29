import mysql.connector
from mysql.connector import Error


class DataRecalculator:
    """
    rh_trade_analysis 테이블의 파생 컬럼들을 일괄적으로 재계산하고 업데이트하는 클래스.
    landAr 등 원본 데이터가 수정되었을 때 데이터 일관성을 유지하기 위해 사용됩니다.
    """

    def __init__(self, db_config):
        self.db_config = db_config
        self.pyeong = 3.305785

    def _get_db_connection(self):
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as e:
            print(f"데이터베이스 연결 중 오류 발생: {e}")
            return None

    def recalculate_and_update_all(self):
        connection = self._get_db_connection()
        if not connection:
            return

        cursor = connection.cursor()

        update_query = f"""
        UPDATE rh_trade_analysis
        SET
            land_price_per_pyeong = CASE
                WHEN landAr > 0 AND CAST(REPLACE(dealAmount, ',', '') AS UNSIGNED) > 0 THEN
                    (CAST(REPLACE(dealAmount, ',', '') AS UNSIGNED) / landAr) * {self.pyeong}
                ELSE 0
            END,
            land_share_ratio = CASE
                WHEN excluUseAr > 0 THEN landAr / excluUseAr
                ELSE 0
            END;
        """

        print("rh_trade_analysis 테이블의 파생 컬럼 재계산을 시작합니다...")
        print("이 작업은 테이블 크기에 따라 몇 분 정도 소요될 수 있습니다.")

        try:
            connection.start_transaction()
            cursor.execute(update_query)
            updated_rows = cursor.rowcount
            connection.commit()

            print(f"\n작업 완료. 총 {updated_rows}개 행의 데이터가 성공적으로 업데이트되었습니다.")

        except Error as e:
            print(f"업데이트 작업 중 오류 발생: {e}")
            connection.rollback()
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("데이터베이스 연결을 닫았습니다.")
