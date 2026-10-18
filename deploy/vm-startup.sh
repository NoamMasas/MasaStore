#!/bin/bash
# Startup script for the MasaStore data VM (Container-Optimized OS, no external IP).
# Runs on every boot: pulls the MySQL/Redis images from Artifact Registry via
# Private Google Access, fetches passwords from Secret Manager, (re)starts both
# containers. Data lives on the stateful partition, so reboots keep it.
# Never `set -x` here: it would echo secrets into the serial console / logs.
set -euo pipefail

MD=http://metadata.google.internal/computeMetadata/v1
md() { curl -sf -H "Metadata-Flavor: Google" "$MD/$1"; }

PROJECT=$(md project/project-id)
REGION=$(md instance/attributes/region)
REPO=$(md instance/attributes/repo)
REGISTRY="${REGION}-docker.pkg.dev"
IMAGE_PREFIX="${REGISTRY}/${PROJECT}/${REPO}"

STATE=/mnt/stateful_partition/masastore
mkdir -p "$STATE/mysql" "$STATE/secrets"
chmod 700 "$STATE/secrets"
export DOCKER_CONFIG="$STATE/docker"

TOKEN=$(md instance/service-accounts/default/token | sed -n 's/.*"access_token" *: *"\([^"]*\)".*/\1/p')

secret() {
  curl -sf -H "Authorization: Bearer $TOKEN" \
    "https://secretmanager.googleapis.com/v1/projects/${PROJECT}/secrets/$1/versions/latest:access" \
    | sed -n 's/.*"data" *: *"\([^"]*\)".*/\1/p' | base64 -d
}

echo "$TOKEN" | docker login -u oauth2accesstoken --password-stdin "https://${REGISTRY}" >/dev/null

MYSQL_APP_PASSWORD=$(secret mysql-app-password)
REDIS_PASSWORD=$(secret redis-password)
if [[ -z "$MYSQL_APP_PASSWORD" || -z "$REDIS_PASSWORD" ]]; then
  echo "masastore startup: failed to read secrets" >&2
  exit 1
fi

umask 077
{
  echo "MYSQL_DATABASE=main"
  echo "MYSQL_USER=masastore"
  echo "MYSQL_PASSWORD=${MYSQL_APP_PASSWORD}"
  # Root is only reachable from inside the container and its password is never
  # stored; it only matters on first init (empty data dir).
  echo "MYSQL_ROOT_PASSWORD=$(head -c 32 /dev/urandom | base64 | tr -d '/+=')"
  echo "MYSQL_ROOT_HOST=localhost"
  echo "TZ=Asia/Jerusalem"
} > "$STATE/secrets/mysql.env"
printf 'requirepass %s\nmaxmemory 48mb\nmaxmemory-policy allkeys-lru\nsave ""\nappendonly no\n' \
  "$REDIS_PASSWORD" > "$STATE/secrets/redis.conf"
chmod 644 "$STATE/secrets/redis.conf"   # redis runs as uid 999 inside the container
umask 022

docker pull -q "${IMAGE_PREFIX}/db:latest"
docker pull -q "${IMAGE_PREFIX}/redis:latest"

docker rm -f masastore-db masastore-redis >/dev/null 2>&1 || true

docker run -d --name masastore-db --restart unless-stopped \
  --env-file "$STATE/secrets/mysql.env" \
  -v "$STATE/mysql:/var/lib/mysql" \
  -p 3306:3306 \
  --memory 450m \
  "${IMAGE_PREFIX}/db:latest" --default-authentication-plugin=mysql_native_password

docker run -d --name masastore-redis --restart unless-stopped \
  -v "$STATE/secrets/redis.conf:/usr/local/etc/redis/redis.conf:ro" \
  -p 6379:6379 \
  --memory 80m \
  "${IMAGE_PREFIX}/redis:latest" redis-server /usr/local/etc/redis/redis.conf

echo "masastore startup: containers started"
