from datetime import datetime

from dateutil.relativedelta import relativedelta

from project_config import get_db_config, get_env_str
from src.real_estate.ingestion import RealEstateDataManager
from utils import load_json_to_dict


if __name__ == "__main__":
    api_service_key = get_env_str("RE_API_SERVICE_KEY", "")
    db_connection_info = get_db_config()

    if not api_service_key:
        raise ValueError("RE_API_SERVICE_KEY 환경 변수가 필요합니다.")

    target_table = "rh_trade_analysis"
    top_10_gu_hcodes_file_path = "./gu_codes.json"

    manager = RealEstateDataManager(api_key=api_service_key, db_config=db_connection_info)

    print("--- 1. 데이터베이스 설정 작업 시작 ---")
    manager.setup_database(main_table_name=target_table)
    print("--- 데이터베이스 설정 완료 ---\n")

    gu_codes_data = load_json_to_dict(top_10_gu_hcodes_file_path) or {}
    top10_gu_hcodes = [gu["code"] for gu in gu_codes_data.get("seoul_top10_gu_codes", [])]

    end_date = datetime.now()
    start_date = end_date - relativedelta(years=20)

    start_ymd = start_date.strftime("%Y%m")
    end_ymd = end_date.strftime("%Y%m")

    print(f"--- 2. 데이터 수집 작업 시작 (기간: {start_ymd}~{end_ymd}) ---")
    manager.run_ingestion(
        lawd_cds=top10_gu_hcodes,
        start_deal_ymd=start_ymd,
        end_deal_ymd=end_ymd,
        table_name=target_table,
    )
    print("--- 모든 데이터 수집 작업 완료 ---")
