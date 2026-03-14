#!/bin/bash
# ==============================================================================
# db_backup_monthly.sh
#
# 월 1회 전체 DB 풀백업을 생성합니다.
# - root .env 단일 소스를 사용
# - 새 백업이 성공적으로 생성된 뒤에만 이전 백업 파일을 삭제
# - 항상 최신 백업 1개만 유지
#
# 사용법:
#   cd /path/to/DataBatcher
#   bash apps/ingest-databatcher/ops/shell/db_backup_monthly.sh
# ==============================================================================

set -euo pipefail

if [ ! -f "db/compose/mysql-standalone/docker-compose-mysql.yaml" ]; then
    echo "Error: 프로젝트 루트 디렉토리에서 실행해주세요."
    echo "  cd /path/to/DataBatcher"
    echo "  bash apps/ingest-databatcher/ops/shell/db_backup_monthly.sh"
    exit 1
fi

ENV_FILE=".env"
COMPOSE_FILE="db/compose/mysql-standalone/docker-compose-mysql.yaml"
BACKUP_DIR="backups/mysql/monthly"
LOG_DIR="logs"

if [ ! -f "${ENV_FILE}" ]; then
    echo "Error: ${ENV_FILE} 파일이 없습니다."
    exit 1
fi

mkdir -p "${BACKUP_DIR}" "${LOG_DIR}"

set -a
# shellcheck disable=SC1091
source "${ENV_FILE}"
set +a

required_vars=(MYSQL_USER MYSQL_PASSWORD MYSQL_DATABASE MYSQL_PORT DATABASE_URL)
for var_name in "${required_vars[@]}"; do
    if [ -z "${!var_name:-}" ]; then
        echo "Error: ${var_name} 값이 비어 있습니다 (${ENV_FILE})."
        exit 1
    fi
done

parsed_db_port=$(python - <<'PY'
import os
from urllib.parse import urlparse

url = os.environ["DATABASE_URL"]
parsed = urlparse(url)
db = parsed.path.lstrip("/")
port = parsed.port or 3306
print(db)
print(port)
PY
)

url_db=$(printf "%s\n" "${parsed_db_port}" | sed -n '1p')
url_port=$(printf "%s\n" "${parsed_db_port}" | sed -n '2p')

if [ "${url_db}" != "${MYSQL_DATABASE}" ]; then
    echo "Error: MYSQL_DATABASE(${MYSQL_DATABASE})와 DATABASE_URL DB(${url_db})가 다릅니다."
    exit 1
fi

if [ "${url_port}" != "${MYSQL_PORT}" ]; then
    echo "Error: MYSQL_PORT(${MYSQL_PORT})와 DATABASE_URL 포트(${url_port})가 다릅니다."
    exit 1
fi

echo "[backup] DB 접속 가능 여부 확인 중..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T mysql \
    sh -lc 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqladmin -uroot -h 127.0.0.1 ping --silent'

ym=$(date +%Y%m)
timestamp=$(date +%Y-%m-%dT%H:%M:%S%z)

if command -v zstd >/dev/null 2>&1; then
    ext="zst"
    compressor_cmd=(zstd -T0 -3 -q)
else
    ext="gz"
    compressor_cmd=(gzip -c)
fi

final_backup="${BACKUP_DIR}/${MYSQL_DATABASE}_full_${ym}.sql.${ext}"
tmp_backup="${final_backup}.tmp"

echo "[backup] 백업 생성 시작: ${final_backup}"
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T mysql \
    sh -lc 'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump -u"$MYSQL_USER" --single-transaction --quick --routines --events --triggers --set-gtid-purged=OFF --no-tablespaces "$MYSQL_DATABASE"' \
    | "${compressor_cmd[@]}" > "${tmp_backup}"

if [ ! -s "${tmp_backup}" ]; then
    echo "Error: 백업 파일이 비어 있습니다: ${tmp_backup}"
    rm -f "${tmp_backup}"
    exit 1
fi

mv "${tmp_backup}" "${final_backup}"

sha_file="${final_backup}.sha256"
meta_file="${final_backup}.meta.txt"

shasum -a 256 "${final_backup}" > "${sha_file}"

cat > "${meta_file}" <<EOF
created_at=${timestamp}
database=${MYSQL_DATABASE}
port=${MYSQL_PORT}
backup_file=${final_backup}
sha256_file=${sha_file}
compression=${ext}
EOF

echo "[backup] 이전 백업 정리 중..."
shopt -s nullglob
for old in "${BACKUP_DIR}/${MYSQL_DATABASE}_full_"*.sql.zst "${BACKUP_DIR}/${MYSQL_DATABASE}_full_"*.sql.gz; do
    if [ "${old}" = "${final_backup}" ]; then
        continue
    fi
    rm -f "${old}" "${old}.sha256" "${old}.meta.txt"
done
shopt -u nullglob

size=$(du -h "${final_backup}" | awk '{print $1}')
echo "[backup] 완료: ${final_backup} (${size})"
echo "[backup] 해시: ${sha_file}"
echo "[backup] 메타: ${meta_file}"
