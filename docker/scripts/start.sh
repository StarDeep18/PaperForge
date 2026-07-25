#!/usr/bin/env bash
# Start PaperForge stack using specified profile (default: dev)
PROFILE="${1:-dev}"
echo "🚀 Starting PaperForge using profile: ${PROFILE}..."
docker compose --profile "${PROFILE}" up -d
