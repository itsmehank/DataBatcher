#!/bin/bash
# ==============================================================================
# db_restore_full.sh
#
# 월간 full dump 파일(.sql.zst/.sql.gz/.sql)을 대상 DB로 복구합니다.
# - MySQL 컨테이너 기동은 별도(수동)로 수행
# - 기본은 기존 DB 유지 + import
# - --recreate-db 옵션 사용 시 DB를 재생성 후 import
#
# 사용법:
#   bash apps/ingest-databatcher/ops/shell/db_restore_full.sh --file backups/mysql/monthly/trade_full_202603.sql.zst
#   bash apps/ingest-databatcher/ops/shell/db_restore_full.sh --file <file> --target-db trade_restore --recreate-db --yes
# ==============================================================================

set -euo pipefail

usage() {
    echo "Usage: bash apps/ingest-databatcher/ops/shell/db_restore_full.sh --file <backup_file> [--target-db <db>] [--recreate-db] [--yes]"
}

if [ ! -f "mysql-standalone/docker-compose-mysql.yaml" ]; then
    echo "Error: 프로젝트 루트 디렉토리에서 실행해주세요."
    echo "  cd /path/to/DataBatcher"
    usage
    exit 1
fi

ENV_FILE=".env"
COMPOSE_FILE="mysql-standalone/docker-compose-mysql.yaml"

if [ ! -f "${ENV_FILE}" ]; then
    echo "Error: ${ENV_FILE} 파일이 없습니다."
    exit 1
fi

set -a
# shellcheck disable=SC1091
source "${ENV_FILE}"
set +a

required_vars=(MYSQL_USER MYSQL_PASSWORD MYSQL_DATABASE MYSQL_PORT MYSQL_ROOT_PASSWORD)
for var_name in "${required_vars[@]}"; do
    if [ -z "${!var_name:-}" ]; then
        echo "Error: ${var_name} 값이 비어 있습니다 (${ENV_FILE})."
        exit 1
    fi
done

backup_file=""
target_db="${MYSQL_DATABASE}"
recreate_db="false"
auto_yes="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --file)
            backup_file="${2:-}"
            shift 2
            ;;
        --target-db)
            target_db="${2:-}"
            shift 2
            ;;
        --recreate-db)
            recreate_db="true"
            shift
            ;;
        --yes)
            auto_yes="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: 알 수 없는 옵션: $1"
            usage
            exit 1
            ;;
    esac
done

if [ -z "${backup_file}" ]; then
    echo "Error: --file 옵션은 필수입니다."
    usage
    exit 1
fi

if [ ! -f "${backup_file}" ]; then
    echo "Error: 백업 파일을 찾을 수 없습니다: ${backup_file}"
    exit 1
fi

echo "[restore] MySQL 접속 가능 여부 확인 중..."
if ! docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T mysql \
    sh -lc 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqladmin -uroot -h 127.0.0.1 ping --silent' >/dev/null 2>&1; then
    echo "Error: MySQL 컨테이너에 접속할 수 없습니다."
    echo "먼저 아래 명령으로 MySQL을 기동하세요:"
    echo "  docker compose -f mysql-standalone/docker-compose-mysql.yaml --env-file .env up -d"
    exit 1
fi

echo "[restore] 파일: ${backup_file}"
echo "[restore] 대상 DB: ${target_db}"
echo "[restore] recreate-db: ${recreate_db}"

if [ "${auto_yes}" != "true" ]; then
    echo ""
    echo "주의: 대상 DB에 데이터가 덮어써질 수 있습니다."
    read -r -p "복구를 진행하시겠습니까? (yes/no): " confirm
    if [ "${confirm}" != "yes" ]; then
        echo "[restore] 취소되었습니다."
        exit 0
    fi
fi

if [ "${recreate_db}" = "true" ]; then
    echo "[restore] 대상 DB 재생성 중..."
    docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T mysql sh -lc \
        "MYSQL_PWD=\"\$MYSQL_ROOT_PASSWORD\" mysql -uroot -e \"DROP DATABASE IF EXISTS \\\`${target_db}\\\`; CREATE DATABASE \\\`${target_db}\\\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL PRIVILEGES ON \\\`${target_db}\\\`.* TO '\$MYSQL_USER'@'%'; FLUSH PRIVILEGES;\""
fi

echo "[restore] 데이터 복구 중..."
if [[ "${backup_file}" == *.zst ]]; then
    zstd -dc "${backup_file}" | docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T mysql \
        sh -lc "MYSQL_PWD=\"\$MYSQL_PASSWORD\" mysql -u\"\$MYSQL_USER\" \"${target_db}\""
elif [[ "${backup_file}" == *.gz ]]; then
    gunzip -c "${backup_file}" | docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T mysql \
        sh -lc "MYSQL_PWD=\"\$MYSQL_PASSWORD\" mysql -u\"\$MYSQL_USER\" \"${target_db}\""
elif [[ "${backup_file}" == *.sql ]]; then
    cat "${backup_file}" | docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T mysql \
        sh -lc "MYSQL_PWD=\"\$MYSQL_PASSWORD\" mysql -u\"\$MYSQL_USER\" \"${target_db}\""
else
    echo "Error: 지원하지 않는 백업 파일 확장자입니다 (.sql/.sql.gz/.sql.zst)."
    exit 1
fi

echo "[restore] 복구 검증 중..."
table_count=$(docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T mysql \
    sh -lc "MYSQL_PWD=\"\$MYSQL_PASSWORD\" mysql -N -u\"\$MYSQL_USER\" -D \"${target_db}\" -e \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();\"")

stock_exists=$(docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T mysql \
    sh -lc "MYSQL_PWD=\"\$MYSQL_PASSWORD\" mysql -N -u\"\$MYSQL_USER\" -D \"${target_db}\" -e \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='stock_prices';\"")

echo "[restore] 완료"
echo "[restore] table_count=${table_count}"
echo "[restore] stock_prices_exists=${stock_exists}"
