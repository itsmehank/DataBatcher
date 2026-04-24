"""
indicators.minervini.trend_template

미너비니 트렌드 템플릿 스크리닝 로직

Mark Minervini의 트렌드 템플릿(Trend Template) 8가지 조건:
1. 현재 주가가 150일 및 200일 이동평균선 위에 있음
2. 150일 이동평균선이 200일 이동평균선 위에 있음
3. 200일 이동평균선이 최소 1개월(22거래일) 상승 추세
4. 50일 이동평균선이 150일, 200일 이동평균선 위에 있음
5. 현재 주가가 50일 이동평균선 위에 있음
6. 현재 주가가 52주 최저가 대비 최소 30% 이상
7. 현재 주가가 52주 최고가의 최소 75% 이상 (고가 근처)
8. RS Rating이 70 이상

추가 필터:
- Blue Dot (선택적): RS Line이 52주 신고가이면서 주가는 신고가가 아님
"""
from __future__ import annotations

import pandas as pd


def _compute_condition_masks(
    prices_wide: pd.DataFrame,
    rs_rating_wide: pd.DataFrame | None,
    config: dict,
) -> dict[str, pd.DataFrame]:
    """
    Compute all 8 Minervini trend template conditions as separate boolean masks.
    Returns a dict mapping condition key -> (dates × symbols) boolean DataFrame.
    Condition keys match _meta/05_GLOSSARY.md Part B.2 `conditions_met` schema.
    """
    sma_50 = prices_wide.rolling(window=50, min_periods=50).mean()
    sma_150 = prices_wide.rolling(window=150, min_periods=150).mean()
    sma_200 = prices_wide.rolling(window=200, min_periods=200).mean()

    lookback_52w = config.get("lookback_52w", 252)
    high_52w = prices_wide.rolling(window=lookback_52w, min_periods=lookback_52w).max()
    low_52w = prices_wide.rolling(window=lookback_52w, min_periods=lookback_52w).min()

    filters = config.get("filters", {})
    sma200_uptrend_lookback = filters.get("sma200_uptrend", {}).get("lookback", 22)
    low_pct = filters.get("price_above_52w_low", {}).get("pct", 1.3)
    high_pct = filters.get("price_near_52w_high", {}).get("pct", 0.75)
    rs_min = filters.get("rs_rating", {}).get("min", 70)

    conditions: dict[str, pd.DataFrame] = {}

    # 1. Price above MA150 and MA200
    conditions["price_above_ma150_ma200"] = (prices_wide > sma_150) & (prices_wide > sma_200)

    # 2. MA150 above MA200
    conditions["ma150_above_ma200"] = sma_150 > sma_200

    # 3. MA200 uptrend (1 month ~22 trading days)
    conditions["ma200_uptrend_1mo"] = sma_200 > sma_200.shift(sma200_uptrend_lookback)

    # 4. MA50 above MA150 and MA200
    conditions["ma50_above_ma150_ma200"] = (sma_50 > sma_150) & (sma_50 > sma_200)

    # 5. Price above MA50
    conditions["price_above_ma50"] = prices_wide > sma_50

    # 6. Price at least 30% above 52-week low
    conditions["price_30pct_above_52w_low"] = prices_wide >= (low_52w * low_pct)

    # 7. Price within 25% of 52-week high
    conditions["price_within_25pct_of_52w_high"] = prices_wide >= (high_52w * high_pct)

    # 8. RS Rating above threshold
    if rs_rating_wide is not None and not rs_rating_wide.empty:
        rs_aligned = rs_rating_wide.reindex_like(prices_wide)
        conditions["rs_rating_above_70"] = rs_aligned >= rs_min
    else:
        conditions["rs_rating_above_70"] = pd.DataFrame(
            False, index=prices_wide.index, columns=prices_wide.columns
        )

    return conditions


def screen_minervini_trend_template(
    prices_wide: pd.DataFrame,
    rs_rating_wide: pd.DataFrame | None,
    blue_dot_wide: pd.DataFrame | None,
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    """
    미너비니 트렌드 템플릿 스크리닝.

    Args:
        prices_wide: 가격 데이터 (dates x symbols), close 가격
        rs_rating_wide: RS Rating 데이터 (dates x symbols) or None
        blue_dot_wide: Blue Dot 데이터 (dates x symbols) or None
        config: 필터 설정 (config['filters'] 섹션)

    Returns:
        (pass_mask, failed_reasons, conditions):
            - pass_mask: 통과한 종목 마스크 (DataFrame, bool)
            - failed_reasons: 탈락 사유 (DataFrame, str) — 현재 미사용, backward compat
            - conditions: dict of condition_key -> (dates × symbols) bool DataFrame
                          8개 조건 전부 포함. pass_mask는 filter toggle을 반영하나
                          conditions dict는 toggle 무관하게 항상 8개 키를 포함한다.
    """
    if prices_wide.empty:
        return pd.DataFrame(), pd.DataFrame(), {}

    filters = config.get("filters", {})
    conditions = _compute_condition_masks(prices_wide, rs_rating_wide, config)

    active_masks: list[pd.DataFrame] = []

    if filters.get("ma_ordering", {}).get("enabled", True):
        active_masks.append(conditions["price_above_ma150_ma200"])
        active_masks.append(conditions["ma150_above_ma200"])
        active_masks.append(conditions["ma50_above_ma150_ma200"])
        active_masks.append(conditions["price_above_ma50"])
    if filters.get("sma200_uptrend", {}).get("enabled", True):
        active_masks.append(conditions["ma200_uptrend_1mo"])
    if filters.get("price_above_52w_low", {}).get("enabled", True):
        active_masks.append(conditions["price_30pct_above_52w_low"])
    if filters.get("price_near_52w_high", {}).get("enabled", True):
        active_masks.append(conditions["price_within_25pct_of_52w_high"])
    if filters.get("rs_rating", {}).get("enabled", True):
        active_masks.append(conditions["rs_rating_above_70"])

    # Blue Dot는 8조건 밖의 별도 선택 필터
    if filters.get("blue_dot", {}).get("enabled", False):
        if blue_dot_wide is not None and not blue_dot_wide.empty:
            bd_aligned = blue_dot_wide.reindex_like(prices_wide)
            active_masks.append(bd_aligned == 1)
        else:
            active_masks.append(
                pd.DataFrame(False, index=prices_wide.index, columns=prices_wide.columns)
            )

    if not active_masks:
        pass_mask = pd.DataFrame(True, index=prices_wide.index, columns=prices_wide.columns)
    else:
        pass_mask = active_masks[0]
        for m in active_masks[1:]:
            pass_mask = pass_mask & m

    return pass_mask, pd.DataFrame(), conditions