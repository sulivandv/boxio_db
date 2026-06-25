# Boxio v2.2.6 — Fase 1 Render + Neon

## Objetivo

Implementar a Fase 1 de produção inicial:

```text
Boxio Desktop
        ↓
Render Web Service executando FastAPI
        ↓
Neon PostgreSQL
```

## Mudanças principais

- Adicionado `render.yaml` na raiz do projeto.
- Adicionado `license_server/Procfile`.
- Adicionado `license_server/runtime.txt
    license_server/scripts/check_deploy.py`.
- Atualizado Dockerfile para respeitar variável `PORT`.
- Adicionada proteção de rotas administrativas por `ADMIN_API_KEY`.
- Adicionado rate limit simples em memória para endpoints públicos.
- Adicionado endpoint `/health/db` para testar conectividade com Neon.
- Atualizados exemplos de `.env` para Render + Neon.
- Atualizada documentação completa da Fase 1.
- Atualizada versão do Boxio para `2.2.6`.

## Arquivos modificados

```text
render.yaml
license_server/Procfile
license_server/runtime.txt
    license_server/scripts/check_deploy.py
license_server/Dockerfile
license_server/.env.example
license_server/app/config.py
license_server/app/database.py
license_server/app/dependencies.py
license_server/app/middleware.py
license_server/app/main.py
license_server/app/routers/admin.py
license_server/app/routers/releases.py
license_server/README.md
deployment/env_examples/license_server.render.env.example
deployment/env_examples/boxio_desktop.render.production.env.example
docs/PRODUCAO_RENDER_FASTAPI_NEON.md
src/core/version.py
```

## Configuração final do desktop

```env
BOXIO_LICENSE_SERVER_URL=https://boxio-license-server.onrender.com
BOXIO_LICENSE_OFFLINE_GRACE_DAYS=7
BOXIO_LICENSE_TIMEOUT=20
```
