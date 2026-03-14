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


def screen_minervini_trend_template(
    prices_wide: pd.DataFrame,
    rs_rating_wide: pd.DataFrame | None,
    blue_dot_wide: pd.DataFrame | None,
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    미너비니 트렌드 템플릿 스크리닝.

    Args:
        prices_wide: 가격 데이터 (dates x symbols), close 가격
        rs_rating_wide: RS Rating 데이터 (dates x symbols) or None
        blue_dot_wide: Blue Dot 데이터 (dates x symbols) or None
        config: 필터 설정 (config['filters'] 섹션)

    Returns:
        (pass_mask, failed_reasons):
            - pass_mask: 통과한 종목 마스크 (DataFrame, bool)
            - failed_reasons: 탈락 사유 (DataFrame, str) — 현재 미사용
    """
    if prices_wide.empty:
        return pd.DataFrame(), pd.DataFrame()

    def _all_false_mask() -> pd.DataFrame:
        return pd.DataFrame(False, index=prices_wide.index, columns=prices_wide.columns)

    # 1. SMA 계산
    sma_50 = prices_wide.rolling(window=50, min_periods=50).mean()
    sma_150 = prices_wide.rolling(window=150, min_periods=150).mean()
    sma_200 = prices_wide.rolling(window=200, min_periods=200).mean()

    # 2. 52주 최고가/최저가 계산
    lookback_52w = config.get("lookback_52w", 252)
    high_52w = prices_wide.rolling(window=lookback_52w, min_periods=lookback_52w).max()
    low_52w = prices_wide.rolling(window=lookback_52w, min_periods=lookback_52w).min()

    # 3. 필터별 마스크 생성
    filters = config.get("filters", {})
    all_masks = []

    # Filter 1: MA 정배열 (price > sma50 > sma150 > sma200)
    if filters.get("ma_ordering", {}).get("enabled", True):
        mask_ma = (
            (prices_wide > sma_50)
            & (sma_50 > sma_150)
            & (sma_150 > sma_200)
        )
        all_masks.append(mask_ma)

    # Filter 2: SMA200 상승 추세 (22거래일 전보다 높음)
    if filters.get("sma200_uptrend", {}).get("enabled", True):
        lookback_uptrend = filters.get("sma200_uptrend", {}).get("lookback", 22)
        sma200_prev = sma_200.shift(lookback_uptrend)
        mask_sma200_up = sma_200 > sma200_prev
        all_masks.append(mask_sma200_up)

    # Filter 3: 52주 저가 대비 최소 pct 이상
    if filters.get("price_above_52w_low", {}).get("enabled", True):
        pct_low = filters.get("price_above_52w_low", {}).get("pct", 1.3)
        mask_above_low = prices_wide >= (low_52w * pct_low)
        all_masks.append(mask_above_low)

    # Filter 4: 52주 고가의 최소 pct 이상
    if filters.get("price_near_52w_high", {}).get("enabled", True):
        pct_high = filters.get("price_near_52w_high", {}).get("pct", 0.75)
        mask_near_high = prices_wide >= (high_52w * pct_high)
        all_masks.append(mask_near_high)

    # Filter 5: RS Rating >= min
    if filters.get("rs_rating", {}).get("enabled", True):
        if rs_rating_wide is not None and not rs_rating_wide.empty:
            min_rs = filters.get("rs_rating", {}).get("min", 70)
            # Align indices/columns with prices_wide
            rs_aligned = rs_rating_wide.reindex_like(prices_wide)
            mask_rs = rs_aligned >= min_rs
            all_masks.append(mask_rs)
        else:
            # Fail-closed: 필터가 enabled인데 입력 데이터가 없으면 전부 탈락 처리
            all_masks.append(_all_false_mask())

    # Filter 6: Blue Dot == 1 (선택적)
    if filters.get("blue_dot", {}).get("enabled", False):
        if blue_dot_wide is not None and not blue_dot_wide.empty:
            bd_aligned = blue_dot_wide.reindex_like(prices_wide)
            mask_bd = bd_aligned == 1
            all_masks.append(mask_bd)
        else:
            # Fail-closed: 필터가 enabled인데 입력 데이터가 없으면 전부 탈락 처리
            all_masks.append(_all_false_mask())

    # 4. 모든 마스크 AND 결합
    if not all_masks:
        # 필터가 하나도 없으면 모두 통과
        pass_mask = pd.DataFrame(True, index=prices_wide.index, columns=prices_wide.columns)
    else:
        pass_mask = all_masks[0]
        for m in all_masks[1:]:
            pass_mask = pass_mask & m

    # failed_reasons는 현재 미사용 (통과 종목만 저장)
    failed_reasons = pd.DataFrame()

    return pass_mask, failed_reasons
