import os

import mysql.connector
import pytest


REQUIRED_DB_ENV = ["RE_DB_HOST", "RE_DB_PORT", "RE_DB_USER", "RE_DB_PASSWORD", "RE_DB_NAME"]


def _skip_if_db_env_missing():
    missing = [key for key in REQUIRED_DB_ENV if not os.getenv(key)]
    if missing:
        pytest.skip(f"DB 환경변수가 없어 테스트를 건너뜁니다: {', '.join(missing)}")


def _connect_db():
    return mysql.connector.connect(
        host=os.getenv("RE_DB_HOST"),
        port=int(os.getenv("RE_DB_PORT")),
        user=os.getenv("RE_DB_USER"),
        password=os.getenv("RE_DB_PASSWORD"),
        database=os.getenv("RE_DB_NAME"),
    )


@pytest.mark.db
def test_pipeline_tables_have_rows():
    _skip_if_db_env_missing()

    conn = _connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM rh_trade_analysis")
            raw_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM monthly_dong_analysis")
            monthly_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM building_transaction_analysis_above_ground")
            above_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM building_transaction_analysis_below_ground")
            below_cnt = cursor.fetchone()[0]

        assert raw_cnt > 0
        assert monthly_cnt > 0
        assert above_cnt > 0
        assert below_cnt >= 0
    finally:
        conn.close()


@pytest.mark.db
def test_combined_api_contract_with_db_data():
    _skip_if_db_env_missing()

    conn = _connect_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT MAX(CONCAT(dealYear, LPAD(dealMonth, 2, '0'))) FROM rh_trade_analysis")
            max_ymd = cursor.fetchone()[0]
    finally:
        conn.close()

    if not max_ymd:
        pytest.skip("원천 데이터가 없어 API 계약 테스트를 건너뜁니다.")

    import web_ui.app as app_module

    client = app_module.app.test_client()
    response = client.post(
        "/combined_analysis",
        json={
            "target_ymd": str(max_ymd),
            "top_percent": 10,
            "analysis_period": 2,
        },
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert "data" in payload
    assert isinstance(payload["data"], list)
