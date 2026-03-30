#!/bin/bash
set -euo pipefail

require_var() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "[setup.sh] missing required env: ${name}" >&2
    exit 1
  fi
}

for required in \
  MYSQL_DATABASE \
  MYSQL_USER \
  MYSQL_PASSWORD \
  MYSQL_ROOT_PASSWORD \
  REAL_ESTATE_DB_NAME \
  REAL_ESTATE_TEST_DB_NAME \
  REAL_ESTATE_DB_USER \
  REAL_ESTATE_DB_PASSWORD; do
  require_var "$required"
done

REAL_ESTATE_SCHEMA_FILE="/opt/bootstrap/real_estate_schema.sql"

if [ ! -f "$REAL_ESTATE_SCHEMA_FILE" ]; then
  echo "[setup.sh] schema file not found: $REAL_ESTATE_SCHEMA_FILE" >&2
  exit 1
fi

mysql_root() {
  mysql -u root -p"${MYSQL_ROOT_PASSWORD}" "$@"
}

create_database_and_grants() {
  local db_name="$1"
  local db_user="$2"
  local db_password="$3"

  mysql_root <<EOSQL
CREATE DATABASE IF NOT EXISTS \
\`${db_name}\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${db_user}'@'%' IDENTIFIED BY '${db_password}';
GRANT ALL PRIVILEGES ON \
\`${db_name}\`.* TO '${db_user}'@'%';
FLUSH PRIVILEGES;
EOSQL
}

apply_schema_file() {
  local db_name="$1"
  mysql_root "$db_name" < "$REAL_ESTATE_SCHEMA_FILE"
}

mysql_root <<EOSQL
CREATE DATABASE IF NOT EXISTS \
\`${MYSQL_DATABASE}_test\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON \
\`${MYSQL_DATABASE}_test\`.* TO '${MYSQL_USER}'@'%';
FLUSH PRIVILEGES;
EOSQL

create_database_and_grants "$REAL_ESTATE_DB_NAME" "$REAL_ESTATE_DB_USER" "$REAL_ESTATE_DB_PASSWORD"
create_database_and_grants "$REAL_ESTATE_TEST_DB_NAME" "$REAL_ESTATE_DB_USER" "$REAL_ESTATE_DB_PASSWORD"

apply_schema_file "$REAL_ESTATE_DB_NAME"
apply_schema_file "$REAL_ESTATE_TEST_DB_NAME"
