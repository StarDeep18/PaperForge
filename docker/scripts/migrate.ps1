param (
    [string]$Profile = "dev"
)
$ContainerName = if ($Profile -eq "prod") { "server-prod" } else { "server" }
Write-Host "📦 Running database migrations in container: $ContainerName..." -ForegroundColor Magenta
docker compose exec $ContainerName python migrate.py
