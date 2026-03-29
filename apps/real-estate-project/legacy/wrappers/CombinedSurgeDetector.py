from project_config import get_db_config
from src.real_estate.detectors.combined import CombinedSurgeDetector


if __name__ == "__main__":
    detector = CombinedSurgeDetector(db_config=get_db_config())

    target_analysis_ymd = "202507"
    target_top_percent = 5.0
    target_analysis_period_months = 6

    print(
        f"\n--- 급등 신호 백테스팅 시작 (기준: {target_analysis_ymd}, 상위: {target_top_percent}%, 기간: {target_analysis_period_months}개월) ---"
    )

    surging_properties = detector.find_surging_properties(
        target_ymd=target_analysis_ymd,
        top_percent=target_top_percent,
        analysis_period_months=target_analysis_period_months,
    )

    if not surging_properties.empty:
        print("\n[백테스팅 결과: 급등 신호 포착 목록]")
        print(surging_properties.to_string())
    else:
        print("\n[백테스팅 결과: 포착된 급등 신호가 없습니다.]")
