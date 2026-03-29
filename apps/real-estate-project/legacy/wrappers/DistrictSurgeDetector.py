from datetime import datetime

from dateutil.relativedelta import relativedelta

from map_drawing import map_utils
from project_config import get_db_config
from src.real_estate.detectors.district import DistrictSurgeDetector


if __name__ == "__main__":
    detector = DistrictSurgeDetector(db_config=get_db_config())

    target_analysis_ymd = "202508"
    target_analysis_period_months = 6

    district_name = input("분석할 동 이름을 입력하세요 (예: 송파동): ")

    try:
        top_n = int(input("상위 몇 개의 결과를 보시겠습니까? (기본값: 10): ") or "10")
    except ValueError:
        print("유효한 숫자가 아닙니다. 기본값 10을 사용합니다.")
        top_n = 10

    print(
        f"\n--- 급등 신호 백테스팅 시작 (기준: {target_analysis_ymd}, 지역: {district_name}, 상위: {top_n}개, 기간: {target_analysis_period_months}개월) ---"
    )

    surging_properties = detector.find_surging_properties(
        target_ymd=target_analysis_ymd,
        district_name=district_name,
        top_n=top_n,
        analysis_period_months=target_analysis_period_months,
    )

    if not surging_properties.empty:
        print("\n[백테스팅 결과: 급등 신호 포착 목록]")
        print(surging_properties.to_string())

        print("\n지도 생성을 위한 주소 변환 중...")
        address_list = []
        for _, row in surging_properties.iterrows():
            address = map_utils.build_address_from_code(row["sggCd"], row["umdNm"], row["jibun"])
            address_list.append(address)

        value_list = surging_properties["surge_score"].tolist()
        start_ymd_str = (
            datetime.strptime(target_analysis_ymd, "%Y%m") - relativedelta(months=target_analysis_period_months - 1)
        ).strftime("%Y%m")
        output_filename = f"{district_name}_{top_n}_{start_ymd_str}_{target_analysis_ymd}.html"
        output_dir = "/Users/hank.es/LocalBigqueryTask/RealEstateProject/map_images"

        print(f"\n지도 생성 중... ({output_filename})")
        map_utils.create_map_with_multiple_addresses(
            address_list=address_list,
            value_list=value_list,
            output_dir=output_dir,
            output_filename=output_filename,
        )
    else:
        print("\n[백테스팅 결과: 포착된 급등 신호가 없습니다.]")
