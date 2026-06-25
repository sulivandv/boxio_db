# Boxio License Server

Servidor API para ativação, validação e gestão de licenças anuais do Boxio.

## Arquitetura Fase 1 recomendada

```text
Boxio Desktop
        ↓
https://boxio-license-server.onrender.com
        ↓
Render Web Service executando FastAPI
        ↓
PostgreSQL Neon
```

## Tecnologias

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL/Neon
- Render Web Service
- GitHub Releases para atualizações futuras

## Rodar localmente

```bash
cd license_server
python -m venv .venv
.venv\Scriptsctivate
pip install -r requirements.txt
copy .env.example .env
```

Configure `DATABASE_URL`, `LICENSE_TOKEN_SECRET` e opcionalmente `ADMIN_API_KEY` no `.env`.

Depois rode:

```bash
uvicorn app.main:app --reload
```

Teste:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/health/db
http://127.0.0.1:8000/docs
```

No Boxio Desktop local:

```env
BOXIO_LICENSE_SERVER_URL=http://127.0.0.1:8000
```

## Produção Fase 1 no Render

Consulte:

```text
docs/PRODUCAO_RENDER_FASTAPI_NEON.md
```

Valores principais no Render:

```text
Root Directory: license_server
Build Command: pip install --upgrade pip && pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

Variáveis obrigatórias:

```env
APP_ENV=production
DATABASE_URL=postgresql+psycopg://boxio_license_user:SENHA_FORTE@HOST_NEON/neondb?sslmode=require
LICENSE_DB_SCHEMA=licensing
LICENSE_TOKEN_SECRET=CHAVE_FORTE_COM_MAIS_DE_32_CARACTERES
ADMIN_API_KEY=CHAVE_ADMIN_FORTE
```

No Boxio Desktop em produção:

```env
BOXIO_LICENSE_SERVER_URL=https://boxio-license-server.onrender.com
```

## Criar uma licença de teste

```bash
python scripts/create_license.py "Clínica Exemplo" BOXIO-2026-0001 2027-05-18
```

## Endpoints do desktop

- `POST /licenses/activate`
- `POST /licenses/validate`
- `POST /licenses/deactivate`

## Aliases

- `POST /api/license/activate`
- `POST /api/license/validate`
- `POST /api/license/heartbeat`
- `POST /api/license/revoke`
- `GET /api/releases/latest`

## Rotas administrativas

As rotas `/admin` exigem header:

```text
X-Admin-API-Key: SUA_ADMIN_API_KEY
```

Se `ADMIN_API_KEY` não estiver configurada, as rotas administrativas ficam desativadas.

## Segurança

Nunca exponha no desktop ou em repositório público:

```text
DATABASE_URL
LICENSE_TOKEN_SECRET
ADMIN_API_KEY
```
