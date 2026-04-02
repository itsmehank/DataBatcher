#!/bin/bash
set -euo pipefail

if [ -z "${MONGO_APP_DB_NAME:-}" ] || [ -z "${MONGO_APP_USERNAME:-}" ] || [ -z "${MONGO_APP_PASSWORD:-}" ]; then
  echo "[mongo-init] app DB credentials are incomplete; skipping app user bootstrap"
  exit 0
fi

mongosh --quiet --authenticationDatabase admin -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" <<EOJS
const dbName = "$MONGO_APP_DB_NAME";
const username = "$MONGO_APP_USERNAME";
const password = "$MONGO_APP_PASSWORD";
const targetDb = db.getSiblingDB(dbName);
const existing = targetDb.getUser(username);

if (!existing) {
  targetDb.createUser({
    user: username,
    pwd: password,
    roles: [{ role: "readWrite", db: dbName }],
  });
  print(`[mongo-init] created app user '${username}' for db '${dbName}'`);
} else {
  targetDb.updateUser(username, {
    pwd: password,
    roles: [{ role: "readWrite", db: dbName }],
  });
  print(`[mongo-init] updated app user '${username}' for db '${dbName}'`);
}
EOJS
