# Boxio - Migração do JSON local para Neon/PostgreSQL
# Execute somente depois de testar a conexão e inicializar o schema.

$backup = "database\inventory_db_backup_antes_neon.json"
if (Test-Path "database\inventory_db.json") {
    Copy-Item "database\inventory_db.json" $backup -Force
    Write-Host "Backup criado em $backup" -ForegroundColor Green
}

python -m src.database.migrations.json_to_postgres --json database/inventory_db.json --company "Inovi"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Falha na migração. O JSON original foi preservado." -ForegroundColor Red
    exit 1
}

Write-Host "Migração concluída." -ForegroundColor Green
