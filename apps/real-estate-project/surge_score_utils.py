import pandas as pd


def calculate_surge_score(group: pd.DataFrame):
    """단일 건물 그룹에 대한 급등 점수와 관련 지표를 계산합니다."""
    if len(group) < 2:
        return None

    first_row = group.iloc[0]
    last_row = group.iloc[-1]

    exclu_first_price = first_row["avg_exclu_price_per_pyeong"]
    exclu_last_price = last_row["avg_exclu_price_per_pyeong"]
    if exclu_first_price is not None and exclu_first_price > 0:
        exclu_cumulative_return = ((exclu_last_price - exclu_first_price) / exclu_first_price) * 100
    else:
        exclu_cumulative_return = 0

    land_first_price = first_row["avg_land_price_per_pyeong"]
    land_last_price = last_row["avg_land_price_per_pyeong"]
    if land_first_price is not None and land_first_price > 0:
        land_cumulative_return = ((land_last_price - land_first_price) / land_first_price) * 100
    else:
        land_cumulative_return = 0

    cumulative_return = max(exclu_cumulative_return or 0, land_cumulative_return or 0)

    reliability_score = group["trade_count"].sum()

    group_name = getattr(group, "name", None)
    grouped_sgg_cd = None
    grouped_jibun = None
    grouped_build_year = None
    if isinstance(group_name, tuple) and len(group_name) == 3:
        grouped_sgg_cd, grouped_jibun, grouped_build_year = group_name

    return pd.Series(
        {
            "sggCd": grouped_sgg_cd if grouped_sgg_cd is not None else last_row["sggCd"],
            "umdNm": last_row["umdNm"],
            "jibun": grouped_jibun if grouped_jibun is not None else last_row["jibun"],
            "buildYear": grouped_build_year if grouped_build_year is not None else last_row["buildYear"],
            "mhouseNm": last_row["mhouseNm"],
            "surge_score": cumulative_return,
            "surge_type": "꾸준한 상승률",
            "reliability_score": reliability_score,
            "latest_trade_ymd": last_row["deal_ymd"],
            "avg_dealAmount": last_row["avg_dealAmount"],
            "floor_type": group["floor_type"].iloc[0],
        }
    )
