# Boxio v2.2.5 — Arquitetura de produção simplificada

## Mudança principal

O Netlify foi removido do fluxo de produção.

## Arquitetura final

```text
Boxio Desktop
        ↓
https://licenses.seudominio.com
        ↓
Nginx + Certbot
        ↓
Docker + FastAPI
        ↓
Neon
```

## Arquivos adicionados/atualizados

```text
docs/PRODUCAO_SIMPLIFICADA_NGINX_DOCKER_CERTBOT_NEON.md
deployment/nginx/boxio-license-server.conf
deployment/nginx/boxio-license-server-http-temp.conf
deployment/docker/docker-compose.production.yml
deployment/docker/docker-compose.for-vps-license-server-folder.yml
deployment/env_examples/license_server.production.env.example
deployment/env_examples/boxio_desktop.production.env.example
```

## Configuração final do desktop

```env
BOXIO_LICENSE_SERVER_URL=https://licenses.seudominio.com
```
