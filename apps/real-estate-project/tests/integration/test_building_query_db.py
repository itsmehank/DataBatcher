import os

import pytest

from building_query.building_transaction_query import BuildingTransactionQuery
from project_config import get_db_config


@pytest.mark.db
def test_building_query_db_smoke():
    if not os.getenv("RE_DB_PASSWORD"):
        pytest.skip("RE_DB_PASSWORD 환경변수가 없어 DB 통합 테스트를 건너뜁니다.")

    query = BuildingTransactionQuery(get_db_config())
    result = query.get_building_transactions("11650", "반포동", "728-33", 1992)
    assert result is not None
