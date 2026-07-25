Write-Host "🛑 Stopping PaperForge containers..." -ForegroundColor Yellow
docker compose --profile dev --profile prod down
