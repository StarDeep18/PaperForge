#!/usr/bin/env bash
# Execute database migrations inside running server container
PROFILE="${1:-dev}"
CONTAINER_NAME="paperforge-server-dev"
if [ "$PROFILE" = "prod" ]; then
    CONTAINER_NAME="paperforge-server-prod"
fi

echo "📦 Running database migrations in container: ${CONTAINER_NAME}..."
docker compose exec "${CONTAINER_NAME}" python migrate.py
