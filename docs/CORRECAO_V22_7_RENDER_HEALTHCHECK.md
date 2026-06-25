# Boxio v2.2.7 — Correção Render Healthcheck

## Problema corrigido

A versão v2.2.6 possuía `healthCheckPath: /health` no `render.yaml`, mas o arquivo `license_server/app/main.py` não declarava explicitamente a rota `/health`.

Isso podia fazer o Render ficar preso na tela:

```text
Incoming HTTP request detected...
Service waking up...
Application Loading
```

ou falhar no health check após o deploy.

## Correções aplicadas

- Adicionada rota pública `GET /health`.
- Mantida rota `GET /health/db` para testar conexão real com o Neon.
- O startup do FastAPI agora não derruba a aplicação inteira se o Neon estiver temporariamente indisponível ou com permissão incorreta.
- O erro de inicialização do banco fica visível por `/health` e `/health/db`.

## Resultado esperado

Teste principal:

```text
https://boxio-license-server.onrender.com/health
```

Resposta esperada:

```json
{
  "ok": true,
  "service": "boxio-license-server",
  "environment": "production",
  "schema": "licensing",
  "database_startup": "ok",
  "database_health": "/health/db"
}
```

Teste do banco:

```text
https://boxio-license-server.onrender.com/health/db
```

Resposta esperada quando o Neon estiver correto:

```json
{
  "ok": true,
  "service": "boxio-license-server",
  "database": "ok"
}
```

Se `/health` funciona, mas `/health/db` falha, o problema está na `DATABASE_URL`, permissões do Neon ou schema `licensing`.
