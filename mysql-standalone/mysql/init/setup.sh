#!/bin/bash
set -euo pipefail

# Expects MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD, MYSQL_ROOT_PASSWORD.
# 01_schema.sql is applied separately via docker-entrypoint-initdb.d.
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL
  CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}_test\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}_test\`.* TO '${MYSQL_USER}'@'%';
  FLUSH PRIVILEGES;
EOSQL
