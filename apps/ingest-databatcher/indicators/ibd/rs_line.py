# indicators/ibd/rs_line.py
"""
RS Line 계산 모듈

개별 종목의 종가를 벤치마크 지수 종가로 나눈 비율(원본 비율).
RS Line이 상승하면 해당 종목이 벤치마크 대비 강세.
"""
from __future__ import annotations

import pandas as pd


def calculate_rs_line(
    stock_close: pd.Series,
    index_close: pd.Series,
) -> pd.Series:
    """
    RS Line = stock_close / index_close (원본 비율).

    Args:
        stock_close: 개별 종목 종가 Series (index=dates)
        index_close: 벤치마크 지수 종가 Series (index=dates)

    Returns:
        RS Line Series (index=dates). 지수 데이터 없는 날짜는 NaN.
    """
    # 날짜 기준으로 정렬 후 나눗셈 (자동 index alignment)
    rs = stock_close / index_close
    return rs


def calculate_rs_line_bulk(
    prices_wide: pd.DataFrame,
    index_close: pd.Series,
) -> pd.DataFrame:
    """
    전 종목 RS Line 일괄 계산 (벡터화).

    Args:
        prices_wide: index=dates, columns=symbols, values=close price
        index_close: 벤치마크 지수 종가 Series (index=dates)

    Returns:
        동일 shape DataFrame. 값 = RS Line 비율.
    """
    # index_close를 DataFrame의 각 컬럼에 나눗셈 (broadcasting)
    return prices_wide.div(index_close, axis=0)
