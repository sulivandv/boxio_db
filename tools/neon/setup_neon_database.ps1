# Boxio - Inicialização do banco Neon/PostgreSQL
# Execute na raiz do projeto após criar o arquivo .env.

Write-Host "Testando conexão com Neon..." -ForegroundColor Cyan
python test_neon_connection.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Falha no teste de conexão. Confira .env, senha e sslmode=require." -ForegroundColor Red
    exit 1
}

Write-Host "Criando/atualizando schema e tabelas do Boxio..." -ForegroundColor Cyan
python -m src.database.postgres.init_db

if ($LASTEXITCODE -ne 0) {
    Write-Host "Falha ao inicializar banco." -ForegroundColor Red
    exit 1
}

Write-Host "Banco Neon configurado com sucesso." -ForegroundColor Green
