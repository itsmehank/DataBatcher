import pytest

from project_config import get_db_config, get_missing_env_keys, validate_db_env


def test_get_missing_env_keys(monkeypatch):
    monkeypatch.delenv("RE_DB_HOST", raising=False)
    monkeypatch.setenv("RE_DB_PORT", "3306")
    missing = get_missing_env_keys(["RE_DB_HOST", "RE_DB_PORT"])
    assert missing == ["RE_DB_HOST"]


def test_validate_db_env_raises_on_missing(monkeypatch):
    for key in ["RE_DB_HOST", "RE_DB_PORT", "RE_DB_USER", "RE_DB_PASSWORD", "RE_DB_NAME"]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError):
        validate_db_env()


def test_get_db_config_returns_env_values(monkeypatch):
    monkeypatch.setenv("RE_DB_HOST", "db.example")
    monkeypatch.setenv("RE_DB_PORT", "3307")
    monkeypatch.setenv("RE_DB_USER", "u")
    monkeypatch.setenv("RE_DB_PASSWORD", "p")
    monkeypatch.setenv("RE_DB_NAME", "real_estate")

    cfg = get_db_config()
    assert cfg["host"] == "db.example"
    assert cfg["port"] == 3307
