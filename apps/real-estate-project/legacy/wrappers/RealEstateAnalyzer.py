from project_config import get_db_config
from src.real_estate.analysis import RealEstateAnalyzer


if __name__ == "__main__":
    source_table = "rh_trade_analysis"
    target_table = "monthly_dong_analysis"

    analyzer = RealEstateAnalyzer(db_config=get_db_config())

    print("--- 1. 2차 분석용 데이터베이스 설정 작업 시작 ---")
    analyzer.setup_database(analysis_table_name=target_table)
    print("--- 2차 분석용 데이터베이스 설정 완료 ---\n")

    print(f"--- 2. '{source_table}' 테이블을 원본으로 2차 분석 작업 시작 ---")
    analyzer.run_analysis(source_table=source_table, target_table=target_table)
    print("--- 모든 2차 분석 작업 완료 ---")
