# indicators/ibd/blue_dot.py
"""
Blue Dot Signal 계산 모듈

RS Line이 52주(252거래일) 신고가인데 주가는 아직 신고가가 아닌 시그널.
이 시그널은 주가가 신고가를 돌파하기 전에 상대강도가 먼저 강세를 보이는 것으로,
IBD/O'Neil 투자법에서 매수 포인트의 선행 지표로 활용된다.
"""
from __future__ import annotations

import pandas as pd


def calculate_blue_dot(
    stock_close: pd.Series,
    rs_line: pd.Series,
    lookback: int = 252,
) -> pd.Series:
    """
    Blue Dot Signal 계산.

    Args:
        stock_close: 개별 종목 종가 Series (index=dates)
        rs_line: RS Line Series (index=dates)
        lookback: rolling max 기간 (기본 252 = 52주)

    Returns:
        Series with 1 (blue dot) or 0 (no signal). NaN for insufficient data.
    """
    rs_rolling_max = rs_line.rolling(window=lookback, min_periods=lookback).max()
    price_rolling_max = stock_close.rolling(window=lookback, min_periods=lookback).max()

    rs_new_high = rs_line >= rs_rolling_max
    price_new_high = stock_close >= price_rolling_max

    blue_dot = (rs_new_high & ~price_new_high).astype(float)

    # lookback 미만 구간은 NaN
    blue_dot.iloc[:lookback - 1] = float("nan")

    return blue_dot


def calculate_blue_dot_bulk(
    prices_wide: pd.DataFrame,
    rs_line_wide: pd.DataFrame,
    lookback: int = 252,
) -> pd.DataFrame:
    """
    전 종목 Blue Dot Signal 일괄 계산 (벡터화).

    Args:
        prices_wide: index=dates, columns=symbols, values=close price
        rs_line_wide: index=dates, columns=symbols, values=RS Line ratio
        lookback: rolling max 기간 (기본 252)

    Returns:
        동일 shape DataFrame. 값 = 1 (blue dot) or 0 (no signal).
    """
    rs_rolling_max = rs_line_wide.rolling(window=lookback, min_periods=lookback).max()
    price_rolling_max = prices_wide.rolling(window=lookback, min_periods=lookback).max()

    rs_new_high = rs_line_wide >= rs_rolling_max
    price_new_high = prices_wide >= price_rolling_max

    blue_dot = (rs_new_high & ~price_new_high).astype(float)

    # lookback 미만 구간은 NaN
    blue_dot.iloc[:lookback - 1] = float("nan")

    return blue_dot
