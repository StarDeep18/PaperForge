param (
    [string]$Profile = "dev"
)
Write-Host "🚀 Starting PaperForge using profile: $Profile..." -ForegroundColor Green
docker compose --profile $Profile up -d
