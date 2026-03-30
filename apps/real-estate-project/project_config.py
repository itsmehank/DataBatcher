import os
import re
import socket
from pathlib import Path
from typing import Any, Dict, Iterable, List

import mysql.connector


REQUIRED_DB_ENV_KEYS = [
    "RE_DB_HOST",
    "RE_DB_PORT",
    "RE_DB_USER",
    "RE_DB_PASSWORD",
    "RE_DB_NAME",
]


def get_missing_env_keys(keys: Iterable[str]) -> List[str]:
    missing = []
    for key in keys:
        value = os.getenv(key)
        if value is None or value == "":
            missing.append(key)
    return missing


def validate_db_env() -> None:
    missing = get_missing_env_keys(REQUIRED_DB_ENV_KEYS)
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"외부 DB 연결을 위해 환경변수가 필요합니다: {joined}")


def get_db_config() -> Dict[str, Any]:
    validate_db_env()
    database = os.environ["RE_DB_NAME"]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", database):
        raise ValueError("RE_DB_NAME 값이 올바르지 않습니다.")
    return {
        "host": os.environ["RE_DB_HOST"],
        "port": int(os.environ["RE_DB_PORT"]),
        "user": os.environ["RE_DB_USER"],
        "password": os.environ["RE_DB_PASSWORD"],
        "database": database,
    }


def get_flask_secret() -> str:
    secret = os.getenv("RE_FLASK_SECRET", "")
    if not secret:
        raise ValueError("RE_FLASK_SECRET 환경변수가 필요합니다.")
    return secret


def get_env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value


_SCHEMA_SQL_PATH = Path(__file__).resolve().parents[2] / "db" / "init" / "03_real_estate_schema.sql"
_schema_initialized = False


def _read_schema_statements() -> List[str]:
    if not _SCHEMA_SQL_PATH.exists():
        raise FileNotFoundError(f"스키마 SQL 파일을 찾을 수 없습니다: {_SCHEMA_SQL_PATH}")

    sql_text = _SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    statements = []
    for statement in sql_text.split(";"):
        stripped = statement.strip()
        if stripped and not stripped.startswith("--"):
            statements.append(stripped)
    return statements


def ensure_schema(db_config: Dict[str, Any]) -> None:
    global _schema_initialized
    if _schema_initialized:
        return

    statements = _read_schema_statements()
    with mysql.connector.connect(**db_config, autocommit=True) as conn:
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)

    _schema_initialized = True
    print(f"스키마 초기화 완료 (db/init/03_real_estate_schema.sql)")


def find_available_port(preferred_port: int, host: str = "127.0.0.1", search_span: int = 50) -> int:
    for port in range(preferred_port, preferred_port + search_span):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex((host, port)) != 0:
                return port
    raise RuntimeError(f"사용 가능한 포트를 찾지 못했습니다. 시작 포트={preferred_port}")
