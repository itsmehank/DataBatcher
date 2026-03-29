def test_district_analysis_gu_path_uses_sgg_filter(monkeypatch, sample_detector_frame):
    monkeypatch.setenv("RE_DB_HOST", "localhost")
    monkeypatch.setenv("RE_DB_PORT", "3306")
    monkeypatch.setenv("RE_DB_USER", "test")
    monkeypatch.setenv("RE_DB_PASSWORD", "test")
    monkeypatch.setenv("RE_DB_NAME", "test")
    monkeypatch.setenv("RE_FLASK_SECRET", "test-secret")

    import src.real_estate.backend.web_app as app_module

    called = {}

    class FakeCombinedDetector:
        def __init__(self, *_args, **_kwargs):
            pass

        def find_surging_properties(self, **kwargs):
            called.update(kwargs)
            return sample_detector_frame

    monkeypatch.setattr(app_module, "CombinedSurgeDetector", FakeCombinedDetector)
    monkeypatch.setattr(app_module.map_utils, "build_address_from_code", lambda *_args, **_kwargs: "서울 송파동 1-1")
    monkeypatch.setattr(app_module.map_utils, "create_map_with_multiple_addresses", lambda **_kwargs: None)

    client = app_module.create_app().test_client()
    response = client.post(
        "/district_analysis",
        json={
            "target_ymd": "202402",
            "gu_name": "송파구",
            "district_name": "",
            "top_n": 5,
            "analysis_period": 6,
        },
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert called["sgg_cd_filter"] == "11710"
    assert called["top_n"] == 5
