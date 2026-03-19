#!/bin/bash
set -e

if [ -z "$MONGO_APP_USERNAME" ] || [ -z "$MONGO_APP_PASSWORD" ]; then
  exit 0
fi

mongosh "$MONGO_INITDB_DATABASE" <<EOJS
db.createUser({
  user: "$MONGO_APP_USERNAME",
  pwd: "$MONGO_APP_PASSWORD",
  roles: [{ role: "readWrite", db: "$MONGO_INITDB_DATABASE" }]
});
EOJS
