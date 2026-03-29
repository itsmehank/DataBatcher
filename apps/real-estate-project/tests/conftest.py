import pandas as pd
import pytest


@pytest.fixture
def sample_surge_group():
    return pd.DataFrame(
        [
            {
                "sggCd": "11710",
                "umdNm": "송파동",
                "jibun": "1-1",
                "buildYear": 2000,
                "mhouseNm": "테스트하우스",
                "deal_ymd": "202401",
                "trade_count": 1,
                "avg_dealAmount": 50000,
                "avg_exclu_price_per_pyeong": 1200,
                "avg_land_price_per_pyeong": 900,
            },
            {
                "sggCd": "11710",
                "umdNm": "송파동",
                "jibun": "1-1",
                "buildYear": 2000,
                "mhouseNm": "테스트하우스",
                "deal_ymd": "202402",
                "trade_count": 2,
                "avg_dealAmount": 55000,
                "avg_exclu_price_per_pyeong": 1380,
                "avg_land_price_per_pyeong": 990,
            },
        ]
    )


@pytest.fixture
def sample_detector_frame():
    return pd.DataFrame(
        [
            {
                "rank": 1,
                "sggCd": "11710",
                "umdNm": "송파동",
                "jibun": "1-1",
                "buildYear": 2000,
                "mhouseNm": "테스트하우스",
                "surge_score": 15.0,
                "reliability_score": 3,
                "latest_trade_ymd": "202402",
                "avg_dealAmount": 55000,
                "floor_type": "지상",
            }
        ]
    )
