import os
import importlib
import pytest


def _reload_config(monkeypatch, env_overrides=None):
    env_overrides = env_overrides or {}
    for key in ["RE_DB_HOST", "RE_DB_PORT", "RE_DB_USER", "RE_DB_PASSWORD", "RE_DB_NAME"]:
        monkeypatch.delenv(key, raising=False)
    for key, val in env_overrides.items():
        monkeypatch.setenv(key, val)

    import project_config
    importlib.reload(project_config)
    return project_config


def test_get_db_config_raises_when_password_missing(monkeypatch):
    cfg = _reload_config(monkeypatch, {
        "RE_DB_HOST": "localhost",
        "RE_DB_PORT": "3306",
        "RE_DB_USER": "testuser",
        "RE_DB_NAME": "testdb",
    })
    with pytest.raises(ValueError, match="RE_DB_PASSWORD"):
        cfg.get_db_config()


def test_get_db_config_raises_when_user_missing(monkeypatch):
    cfg = _reload_config(monkeypatch, {
        "RE_DB_HOST": "localhost",
        "RE_DB_PORT": "3306",
        "RE_DB_PASSWORD": "secret",
        "RE_DB_NAME": "testdb",
    })
    with pytest.raises(ValueError, match="RE_DB_USER"):
        cfg.get_db_config()


def test_get_db_config_succeeds_with_all_vars(monkeypatch):
    cfg = _reload_config(monkeypatch, {
        "RE_DB_HOST": "myhost",
        "RE_DB_PORT": "3307",
        "RE_DB_USER": "myuser",
        "RE_DB_PASSWORD": "mypass",
        "RE_DB_NAME": "mydb",
    })
    result = cfg.get_db_config()
    assert result["host"] == "myhost"
    assert result["port"] == 3307
    assert result["user"] == "myuser"
    assert result["password"] == "mypass"
    assert result["database"] == "mydb"


def test_get_db_config_no_fallback_to_1234(monkeypatch):
    cfg = _reload_config(monkeypatch, {
        "RE_DB_HOST": "localhost",
        "RE_DB_PORT": "3306",
        "RE_DB_USER": "user",
        "RE_DB_NAME": "db",
    })
    with pytest.raises(ValueError):
        result = cfg.get_db_config()
        assert result.get("password") != "1234"


def test_get_db_config_no_fallback_to_root(monkeypatch):
    cfg = _reload_config(monkeypatch, {
        "RE_DB_HOST": "localhost",
        "RE_DB_PORT": "3306",
        "RE_DB_PASSWORD": "pass",
        "RE_DB_NAME": "db",
    })
    with pytest.raises(ValueError):
        result = cfg.get_db_config()
        assert result.get("user") != "root"


def test_get_db_config_rejects_invalid_db_name(monkeypatch):
    cfg = _reload_config(monkeypatch, {
        "RE_DB_HOST": "localhost",
        "RE_DB_PORT": "3306",
        "RE_DB_USER": "user",
        "RE_DB_PASSWORD": "pass",
        "RE_DB_NAME": "real_estate; DROP DATABASE real_estate",
    })
    with pytest.raises(ValueError, match="RE_DB_NAME"):
        cfg.get_db_config()
