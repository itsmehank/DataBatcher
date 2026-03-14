# indicators/ibd/rs_rating.py
"""
IBD RS Rating 계산 모듈

전 종목 횡단면(cross-sectional) 기반으로 1~99 상대강도 백분위 순위를 계산한다.
개별 종목 단위가 아닌, 전체 시장 대비 상대 순위를 산출하므로
기존 BaseIndicator → IndicatorPipeline 패턴과 분리하여 배치 스크립트에서 직접 호출한다.
"""
from __future__ import annotations

import pandas as pd


def calculate_ibd_rs_rating(
    prices_wide: pd.DataFrame,
    weights: dict[str, float] | None = None,
    strict_12m: bool = True,
) -> pd.DataFrame:
    """
    IBD RS Rating 계산 (전 종목 횡단면 백분위).

    Args:
        prices_wide: index=dates(DatetimeIndex), columns=symbols, values=close price.
                     날짜 오름차순 정렬 가정.
        weights: 기간별 가중치. 기본 {'3m': 0.4, '6m': 0.2, '9m': 0.2, '12m': 0.2}
        strict_12m:
            - True: 12개월(252거래일) 미만 데이터 종목은 NaN 처리
            - False: 가용 구간(3/6/9/12m)만으로 가중치를 재정규화해 계산

    Returns:
        동일 shape DataFrame. 값 = 1~99 RS Rating (int).
        데이터 부족한 셀은 NaN.
    """
    if weights is None:
        weights = {"3m": 0.4, "6m": 0.2, "9m": 0.2, "12m": 0.2}

    # 기간별 영업일 수
    periods = {"3m": 63, "6m": 126, "9m": 189, "12m": 252}

    # 기간별 수익률 계산 (percent change over N trading days)
    returns = {}
    for label, days in periods.items():
        returns[label] = prices_wide / prices_wide.shift(days) - 1

    if strict_12m:
        # 기본 가중합 계산
        weighted_sum = sum(returns[label] * weights[label] for label in periods)
        # 252일 전 데이터가 없는 셀(=12개월 수익률이 NaN)은 결과도 NaN
        mask_insufficient = returns["12m"].isna()
        weighted_sum = weighted_sum.where(~mask_insufficient)
    else:
        # 가용 구간만 사용해 가중치를 재정규화한다.
        # 예) 12m NaN이면 3m/6m/9m의 원가중치 합(0.8)으로 나눠 스케일 보정
        weighted_numerator = sum(
            returns[label].fillna(0.0) * weights[label] for label in periods
        )
        available_weight = sum(
            (~returns[label].isna()).astype(float) * weights[label] for label in periods
        )
        weighted_sum = weighted_numerator.div(available_weight.where(available_weight > 0))

    # 횡단면 백분위 순위 (각 날짜별로 rank)
    # pct=True → 0.0 ~ 1.0 비율, * 100 → 0 ~ 100
    rs_rating = weighted_sum.rank(axis=1, pct=True, na_option="keep") * 100

    # clip to 1~99 and round
    rs_rating = rs_rating.clip(lower=1, upper=99).round(0)

    return rs_rating
