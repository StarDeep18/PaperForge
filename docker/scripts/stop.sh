#!/usr/bin/env bash
# Stop PaperForge stack across dev and prod profiles
echo "🛑 Stopping PaperForge containers..."
docker compose --profile dev --profile prod down
