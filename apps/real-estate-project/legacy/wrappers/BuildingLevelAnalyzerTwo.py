from project_config import get_db_config
from src.real_estate.analyzers.building_level_two import BuildingLevelAnalyzer


if __name__ == "__main__":
    SOURCE_TABLE = "rh_trade_analysis"
    TARGET_TABLE = "building_transaction_analysis"

    analyzer = BuildingLevelAnalyzer(db_config=get_db_config())

    print("--- 1. 건물 단위 분석용 데이터베이스 설정 작업 시작 ---")
    analyzer.setup_database(analysis_table_name=TARGET_TABLE)
    print("--- 건물 단위 분석용 데이터베이스 설정 완료 ---\n")

    print(f"--- 2. '{SOURCE_TABLE}' 테이블을 원본으로 건물 단위 분석 작업 시작 ---")
    analyzer.run_analysis(source_table=SOURCE_TABLE, target_table=TARGET_TABLE)
    print("--- 모든 건물 단위 분석 작업 완료 ---")
