import pandas as pd

from src.real_estate.detectors import CombinedSurgeDetector


def test_find_surging_properties_supports_top_n(monkeypatch):
    detector = CombinedSurgeDetector({"host": "localhost"})

    mock_rows = pd.DataFrame(
        [
            {
                "sggCd": "11710",
                "umdNm": "송파동",
                "jibun": "1-1",
                "buildYear": 2000,
                "mhouseNm": "A",
                "surge_score": 50.0,
                "reliability_score": 3,
                "latest_trade_ymd": "202402",
                "avg_dealAmount": 1000,
                "floor_type": "지상",
            },
            {
                "sggCd": "11710",
                "umdNm": "송파동",
                "jibun": "1-2",
                "buildYear": 2001,
                "mhouseNm": "B",
                "surge_score": 20.0,
                "reliability_score": 2,
                "latest_trade_ymd": "202402",
                "avg_dealAmount": 900,
                "floor_type": "지하",
            },
        ]
    )

    monkeypatch.setattr(detector, "_get_data_from_table", lambda *args, **kwargs: mock_rows)

    result = detector.find_surging_properties("202402", top_percent=100.0, analysis_period_months=2, top_n=1)

    assert len(result) == 1
    assert result.iloc[0]["rank"] == 1
    assert result.iloc[0]["surge_score"] == 50.0
