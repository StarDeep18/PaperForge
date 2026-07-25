param (
    [string]$Profile = "dev"
)
Write-Host "🔄 Rebuilding PaperForge containers using profile: $Profile..." -ForegroundColor Cyan
docker compose --profile $Profile build --no-cache
docker compose --profile $Profile up -d
