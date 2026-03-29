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


_SCHEMA_SQL_PATH = Path(__file__).parent / "sql" / "init_schema.sql"
_schema_initialized = False


def ensure_schema(db_config: Dict[str, Any]) -> None:
    """sql/init_schema.sql을 실행하여 DB와 전체 테이블을 초기화한다.

    CREATE TABLE IF NOT EXISTS 기반이므로 여러 번 호출해도 안전하다.
    프로세스 내에서 최초 1회만 실행되고, 이후 호출은 무시된다.
    """
    global _schema_initialized
    if _schema_initialized:
        return

    if not _SCHEMA_SQL_PATH.exists():
        raise FileNotFoundError(f"스키마 SQL 파일을 찾을 수 없습니다: {_SCHEMA_SQL_PATH}")

    sql_text = _SCHEMA_SQL_PATH.read_text(encoding="utf-8")

    # DB 생성은 database 지정 없이 연결해야 하므로 분리
    db_info = db_config.copy()
    db_name = db_info.pop("database")

    with mysql.connector.connect(**db_info) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")

    # 전체 스키마 실행 — DDL 전용 파일이므로 세미콜론 분리가 안전
    with mysql.connector.connect(**db_config, autocommit=True) as conn:
        with conn.cursor() as cursor:
            for statement in sql_text.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    cursor.execute(statement)

    _schema_initialized = True
    print(f"스키마 초기화 완료 (sql/init_schema.sql)")


def find_available_port(preferred_port: int, host: str = "127.0.0.1", search_span: int = 50) -> int:
    for port in range(preferred_port, preferred_port + search_span):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex((host, port)) != 0:
                return port
    raise RuntimeError(f"사용 가능한 포트를 찾지 못했습니다. 시작 포트={preferred_port}")
