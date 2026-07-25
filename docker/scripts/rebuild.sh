#!/usr/bin/env bash
# Rebuild and restart PaperForge stack without cache
PROFILE="${1:-dev}"
echo "🔄 Rebuilding PaperForge containers using profile: ${PROFILE}..."
docker compose --profile "${PROFILE}" build --no-cache
docker compose --profile "${PROFILE}" up -d
