# Boxio — Fase 1: Produção inicial com Render + Neon

## Arquitetura da Fase 1

```text
Boxio Desktop
        ↓
https://boxio-license-server.onrender.com
        ↓
Render Web Service executando FastAPI
        ↓
PostgreSQL Neon
```

Esta fase substitui a complexidade de VPS, Nginx, Certbot, Docker manual e Oracle Cloud por uma implantação mais simples em Render.

## O que foi implementado no projeto

```text
render.yaml
license_server/Procfile
license_server/runtime.txt
license_server/app/dependencies.py
license_server/app/middleware.py
deployment/env_examples/license_server.render.env.example
deployment/env_examples/boxio_desktop.render.production.env.example
```

Também foram ajustados:

```text
license_server/app/config.py
license_server/app/database.py
license_server/app/main.py
license_server/app/routers/admin.py
license_server/app/routers/releases.py
license_server/Dockerfile
license_server/.env.example
src/core/version.py
```

## 1. Preparar Neon

No pgAdmin ou Neon SQL Editor, crie o schema de licenciamento:

```sql
CREATE SCHEMA IF NOT EXISTS licensing;
```

Crie o usuário do servidor de licenças:

```sql
CREATE USER boxio_license_user WITH PASSWORD 'SENHA_FORTE_AQUI';

GRANT USAGE, CREATE ON SCHEMA licensing TO boxio_license_user;

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA licensing
TO boxio_license_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA licensing
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES TO boxio_license_user;
```

A string usada no Render deve ter este formato:

```env
DATABASE_URL=postgresql+psycopg://boxio_license_user:SENHA_FORTE@HOST_NEON/neondb?sslmode=require
```

## 2. Enviar o projeto para GitHub

O Render lê o projeto a partir de um repositório Git.

Recomendado:

```text
repositório privado no GitHub
branch main
render.yaml na raiz do projeto
license_server/ como rootDir do serviço
```

Não envie arquivos `.env` reais para o GitHub.

## 3. Criar Web Service no Render

### Opção A — Blueprint com render.yaml

1. Entre no Render.
2. Clique em **New**.
3. Escolha **Blueprint**.
4. Conecte o repositório do Boxio.
5. Confirme o arquivo `render.yaml`.
6. Preencha as variáveis marcadas como `sync: false`.

### Opção B — Web Service manual

1. Clique em **New**.
2. Escolha **Web Service**.
3. Conecte o repositório.
4. Configure:

```text
Name: boxio-license-server
Runtime: Python
Root Directory: license_server
Build Command: pip install --upgrade pip && pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
Plan: Free ou Starter
```

## 4. Variáveis de ambiente no Render

Configure em:

```text
Render Dashboard
→ boxio-license-server
→ Environment
→ Add Environment Variable
```

Use:

```env
APP_ENV=production
DATABASE_URL=postgresql+psycopg://boxio_license_user:SENHA_FORTE@HOST_NEON/neondb?sslmode=require
LICENSE_DB_SCHEMA=licensing
LICENSE_TOKEN_SECRET=COLOQUE_UMA_CHAVE_LONGA_FORTE_E_PRIVADA
ADMIN_API_KEY=COLOQUE_UMA_CHAVE_ADMIN_FORTE
CORS_ORIGINS=*
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE_SECONDS=1800
GITHUB_OWNER=sua-conta-ou-empresa
GITHUB_REPO=boxio-releases
UPDATE_CHANNEL=stable
```

`LICENSE_TOKEN_SECRET` precisa ter pelo menos 32 caracteres em produção.

`ADMIN_API_KEY` protege as rotas `/admin`. Se ficar vazio, as rotas administrativas ficam bloqueadas.

## 5. Validar deploy

Depois do deploy, abra:

```text
https://boxio-license-server.onrender.com/health
```

Resultado esperado:

```json
{
  "ok": true,
  "service": "boxio-license-server",
  "environment": "production",
  "schema": "licensing"
}
```

Teste também o banco:

```text
https://boxio-license-server.onrender.com/health/db
```

Resultado esperado:

```json
{
  "ok": true,
  "service": "boxio-license-server",
  "database": "ok"
}
```

## 6. Validar pelo terminal

Depois do deploy, você também pode validar pelo terminal:

```bash
cd license_server
python scripts/check_deploy.py https://boxio-license-server.onrender.com
```

O script testa `/health` e `/health/db`.

## 7. Criar licença de teste

Para Fase 1, a forma mais segura é criar licença pelo script, usando `.env` local apontando para o Neon de produção.

No seu computador:

```bash
cd license_server
python -m venv .venv
.venv\Scriptsctivate
pip install -r requirements.txt
copy .env.example .env
```

Preencha o `.env` com a mesma `DATABASE_URL` do Neon.

Depois rode:

```bash
python scripts/create_license.py "Cliente Produção" BOXIO-2026-CLIENTE001 2027-05-18
```

## 8. Configurar Boxio Desktop

No `.env` do Boxio Desktop:

```env
BOXIO_LICENSE_SERVER_URL=https://boxio-license-server.onrender.com
BOXIO_LICENSE_OFFLINE_GRACE_DAYS=7
BOXIO_LICENSE_TIMEOUT=20
```

O timeout foi aumentado para 20 segundos porque serviços gratuitos podem demorar mais na primeira chamada após ficarem inativos.

## 9. Teste completo

1. Abra o Boxio Desktop.
2. Informe a licença:

```text
BOXIO-2026-CLIENTE001
```

3. No pgAdmin/Neon, confira:

```sql
SELECT device_name, app_version, status, activated_at, last_seen_at
FROM licensing.device_activations
ORDER BY activated_at DESC;
```

4. Verifique eventos:

```sql
SELECT event_type, event_status, message, device_name, created_at
FROM licensing.license_events
ORDER BY created_at DESC
LIMIT 30;
```

## 10. Testes obrigatórios

### Revogação

```sql
UPDATE licensing.licenses
SET status = 'revoked', revoked_at = now()
WHERE license_key = 'BOXIO-2026-CLIENTE001';
```

O Boxio deve bloquear na próxima abertura/validação.

Restaurar:

```sql
UPDATE licensing.licenses
SET status = 'active', revoked_at = NULL
WHERE license_key = 'BOXIO-2026-CLIENTE001';
```

### Vencimento

```sql
UPDATE licensing.licenses
SET expires_at = CURRENT_DATE - INTERVAL '1 day', status = 'active'
WHERE license_key = 'BOXIO-2026-CLIENTE001';
```

O Boxio deve bloquear.

Restaurar:

```sql
UPDATE licensing.licenses
SET expires_at = '2027-05-18', status = 'active', revoked_at = NULL
WHERE license_key = 'BOXIO-2026-CLIENTE001';
```

### Limite de dispositivos

```sql
UPDATE licensing.licenses
SET max_devices = 1
WHERE license_key = 'BOXIO-2026-CLIENTE001';
```

Tente ativar em outro computador. O segundo dispositivo deve ser bloqueado se exceder o limite.

## 11. Rotas administrativas protegidas

As rotas `/admin` agora exigem header:

```text
X-Admin-API-Key: SUA_ADMIN_API_KEY
```

Exemplo para criar cliente:

```bash
curl -X POST "https://boxio-license-server.onrender.com/admin/customers" ^
  -H "Content-Type: application/json" ^
  -H "X-Admin-API-Key: SUA_ADMIN_API_KEY" ^
  -d "{"company_name":"Clínica Exemplo"}"
```

## 12. Checklist Fase 1

```text
[ ] Projeto enviado para GitHub
[ ] Render Web Service criado
[ ] Root Directory = license_server
[ ] Build Command configurado
[ ] Start Command configurado com $PORT
[ ] DATABASE_URL configurada com Neon
[ ] LICENSE_TOKEN_SECRET forte configurada
[ ] ADMIN_API_KEY configurada
[ ] /health funcionando
[ ] /health/db funcionando
[ ] Licença criada no Neon
[ ] Boxio Desktop aponta para URL Render
[ ] Ativação funciona
[ ] Revogação bloqueia
[ ] Vencimento bloqueia
[ ] Limite de dispositivos funciona
```


---

# Observação v2.2.7 — tela Application Loading no Render

Se ao abrir `/health` aparecer a tela do Render com `Service waking up`, aguarde até 2 minutos e atualize a página.

Se continuar carregando, verifique:

```text
Render Dashboard → boxio-license-server → Logs
Render Dashboard → boxio-license-server → Deploys
```

A rota principal de health check agora é:

```text
/health
```

A rota de diagnóstico do Neon é:

```text
/health/db
```

Se `/health` abrir e `/health/db` falhar, o FastAPI está online, mas há problema na conexão com o Neon ou nas permissões do banco.
