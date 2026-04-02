# Mongo Standalone (Docker Compose)

This directory provides the shared MongoDB bootstrap for `apps/my-insight-archieve`.

## Files

- `docker-compose-mongo.yaml`: MongoDB-only Docker Compose file
- `mongo-init/01_create_app_user.sh`: creates the app DB user with `readWrite`
- root `.env`: bootstrap contract (single source of truth for shared Mongo startup)

## Quick Start

1. Prepare root env file from the monorepo root:

   ```bash
   cp .env.example .env
   ```

2. Update the Mongo bootstrap values in root `.env`:

   - `MONGO_INITDB_ROOT_USERNAME`
   - `MONGO_INITDB_ROOT_PASSWORD`
   - `MONGO_APP_DB_NAME`
   - `MONGO_APP_USERNAME`
   - `MONGO_APP_PASSWORD`
   - `MONGO_PORT`

3. Start shared Mongo from the monorepo root:

   ```bash
   docker compose -f db/compose/mongo-standalone/docker-compose-mongo.yaml --env-file .env up -d
   ```

4. Check status:

   ```bash
   docker compose -f db/compose/mongo-standalone/docker-compose-mongo.yaml --env-file .env ps
   ```

5. View logs:

   ```bash
   docker compose -f db/compose/mongo-standalone/docker-compose-mongo.yaml --env-file .env logs -f mongodb
   ```

## Runtime Contract

- Shared Mongo infrastructure creates the instance, root account, app database, and app user.
- `apps/my-insight-archieve` consumes only `MONGODB_URI` at runtime.
- App-domain bootstrap stays inside the app:
  - admin account document seed
  - default category seed
  - Mongoose schemas/index behavior
  - backup API behavior

## Connection Examples

- Docker app stack -> shared Mongo on shared Docker network:

  ```text
  mongodb://<app_user>:<app_password>@shared-mongo:27017/<app_db>?authSource=<app_db>
  ```

- Local non-Docker app -> shared Mongo via published port:

  ```text
  mongodb://<app_user>:<app_password>@127.0.0.1:<mongo_port>/<app_db>?authSource=<app_db>
  ```

## Reset

Because the user says existing local Mongo data is disposable, full reset can be done with:

```bash
docker compose -f db/compose/mongo-standalone/docker-compose-mongo.yaml --env-file .env down -v
```
