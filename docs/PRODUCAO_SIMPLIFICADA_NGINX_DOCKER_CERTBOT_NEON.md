# Boxio — Produção simplificada com Nginx, Certbot, Docker, FastAPI e Neon

## 1. Arquitetura final

```text
Boxio Desktop
        ↓
https://licenses.seudominio.com
        ↓
Nginx + Certbot
        ↓
Docker + FastAPI
        ↓
Neon PostgreSQL
```

Nesta arquitetura, o Netlify não é necessário.

## 2. O que cada tecnologia faz

**Boxio Desktop** é o programa instalado no computador do cliente. Ele valida a licença usando:

```env
BOXIO_LICENSE_SERVER_URL=https://licenses.seudominio.com
```

**Nginx** recebe as requisições públicas HTTPS e encaminha para o FastAPI local em `http://127.0.0.1:8000`.

**Certbot** gera o certificado HTTPS gratuito com Let's Encrypt.

**Docker** roda o `license_server` em um container isolado.

**FastAPI** é o backend Python do servidor de licenças em `license_server/`.

**Neon** é o PostgreSQL online que guarda clientes, licenças, ativações e eventos.

## 3. Pré-requisitos

```text
[ ] Uma VPS Ubuntu 22.04 ou 24.04
[ ] Acesso SSH à VPS
[ ] Um domínio/subdomínio apontando para a VPS
[ ] Banco Neon configurado
[ ] Projeto Boxio extraído
[ ] Senha do Neon trocada, se foi exposta
```

Exemplo de domínio:

```text
licenses.seudominio.com
```

## 4. Configurar DNS

No painel do seu domínio, crie:

```text
Tipo: A
Nome: licenses
Valor: IP_DA_SUA_VPS
TTL: automático ou 3600
```

Teste no Windows:

```powershell
ping licenses.seudominio.com
```

O IP retornado deve ser o IP da VPS.

## 5. Configurar Neon/PostgreSQL

No pgAdmin ou Neon SQL Editor:

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

Se o desktop ainda acessa o Neon diretamente, crie também:

```sql
CREATE USER boxio_app_user WITH PASSWORD 'SENHA_FORTE_APP_AQUI';

GRANT USAGE ON SCHEMA boxio TO boxio_app_user;

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA boxio
TO boxio_app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA boxio
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES TO boxio_app_user;
```

String correta do servidor:

```env
DATABASE_URL=postgresql+psycopg://boxio_license_user:SENHA_FORTE@HOST_NEON/neondb?sslmode=require
```

## 6. Acessar a VPS

```powershell
ssh ubuntu@IP_DA_VPS
```

ou:

```powershell
ssh root@IP_DA_VPS
```

## 7. Atualizar VPS e instalar utilitários

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip nano ufw nginx certbot python3-certbot-nginx
```

## 8. Configurar firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
sudo ufw status
```

Resultado esperado:

```text
22/tcp ALLOW
80/tcp ALLOW
443/tcp ALLOW
```

## 9. Instalar Docker

```bash
sudo apt remove -y docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc || true
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

Adicione o repositório:

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

Instale:

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo docker run hello-world
```

## 10. Enviar `license_server` para a VPS

Na VPS:

```bash
sudo mkdir -p /opt/boxio-license-server
sudo chown -R $USER:$USER /opt/boxio-license-server
```

No Windows:

```powershell
scp -r D:\boxio_v22\license_server ubuntu@IP_DA_VPS:/opt/boxio-license-server
```

Na VPS:

```bash
ls -la /opt/boxio-license-server
```

Você precisa ver:

```text
app/
scripts/
Dockerfile
docker-compose.yml
requirements.txt
```

Se ficou `/opt/boxio-license-server/license_server/app`, reorganize:

```bash
mv /opt/boxio-license-server/license_server/* /opt/boxio-license-server/
rm -rf /opt/boxio-license-server/license_server
```

## 11. Criar `.env` de produção

```bash
cd /opt/boxio-license-server
nano .env
```

Conteúdo:

```env
DATABASE_URL=postgresql+psycopg://boxio_license_user:SENHA_FORTE@HOST_NEON/neondb?sslmode=require
LICENSE_DB_SCHEMA=licensing
LICENSE_TOKEN_SECRET=COLOQUE_UMA_CHAVE_LONGA_FORTE_E_PRIVADA
APP_ENV=production
CORS_ORIGINS=*
GITHUB_OWNER=sulivan-dev
GITHUB_REPO=boxio-releases
UPDATE_CHANNEL=stable
```

## 12. Configurar Docker Compose

```bash
nano docker-compose.yml
```

Use:

```yaml
services:
  boxio-license-server:
    build: .
    container_name: boxio-license-server
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "127.0.0.1:8000:8000"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()\""]
      interval: 30s
      timeout: 8s
      retries: 3
      start_period: 20s
```

Suba:

```bash
sudo docker compose up -d --build
```

Valide:

```bash
sudo docker ps
sudo docker logs -f boxio-license-server
curl http://127.0.0.1:8000/health
```

Resultado esperado:

```json
{"ok":true,"service":"boxio-license-server"}
```

## 13. Configurar Nginx temporário HTTP

```bash
sudo nano /etc/nginx/sites-available/boxio-license-server
```

Use, trocando o domínio:

```nginx
server {
    listen 80;
    server_name licenses.seudominio.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto http;
    }
}
```

Ative:

```bash
sudo ln -s /etc/nginx/sites-available/boxio-license-server /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Teste:

```bash
curl http://licenses.seudominio.com/health
```

## 14. Ativar HTTPS com Certbot

```bash
sudo certbot --nginx -d licenses.seudominio.com
```

Escolha redirecionar HTTP para HTTPS.

Teste renovação:

```bash
sudo certbot renew --dry-run
```

Teste HTTPS:

```bash
curl https://licenses.seudominio.com/health
```

## 15. Aplicar Nginx final

Depois do Certbot, use:

```text
deployment/nginx/boxio-license-server.conf
```

ou edite manualmente:

```bash
sudo nano /etc/nginx/sites-available/boxio-license-server
```

Use:

```nginx
limit_req_zone $binary_remote_addr zone=boxio_license_api:10m rate=10r/s;

server {
    listen 80;
    server_name licenses.seudominio.com;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name licenses.seudominio.com;

    ssl_certificate /etc/letsencrypt/live/licenses.seudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/licenses.seudominio.com/privkey.pem;

    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy no-referrer always;
    add_header Cache-Control "no-store" always;

    client_max_body_size 2m;

    location / {
        limit_req zone=boxio_license_api burst=30 nodelay;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        proxy_connect_timeout 15s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

Valide:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 16. Configurar Boxio Desktop

No `.env` do Boxio Desktop:

```env
BOXIO_LICENSE_SERVER_URL=https://licenses.seudominio.com
BOXIO_LICENSE_OFFLINE_GRACE_DAYS=7
BOXIO_LICENSE_TIMEOUT=12
```

Se o desktop acessa Neon diretamente:

```env
BOXIO_DB_MODE=postgresql
BOXIO_DB_SCHEMA=boxio
BOXIO_DATABASE_URL=postgresql+psycopg://boxio_app_user:SENHA_FORTE@HOST_NEON/neondb?sslmode=require
```

## 17. Criar licença real

Na VPS:

```bash
cd /opt/boxio-license-server
sudo docker compose exec boxio-license-server python scripts/create_license.py "Cliente Produção" BOXIO-2026-CLIENTE001 2027-05-18
```

No pgAdmin:

```sql
SELECT license_key, plan, status, expires_at, max_devices, max_users
FROM licensing.licenses
WHERE license_key = 'BOXIO-2026-CLIENTE001';
```

## 18. Testar o fluxo completo

No Boxio Desktop, informe:

```text
BOXIO-2026-CLIENTE001
```

No pgAdmin:

```sql
SELECT device_name, app_version, status, activated_at, last_seen_at
FROM licensing.device_activations
ORDER BY activated_at DESC;
```

Eventos:

```sql
SELECT event_type, event_status, message, device_name, created_at
FROM licensing.license_events
ORDER BY created_at DESC
LIMIT 30;
```

## 19. Testes obrigatórios

### Licença revogada

```sql
UPDATE licensing.licenses
SET status = 'revoked', revoked_at = now()
WHERE license_key = 'BOXIO-2026-CLIENTE001';
```

Restaurar:

```sql
UPDATE licensing.licenses
SET status = 'active', revoked_at = NULL
WHERE license_key = 'BOXIO-2026-CLIENTE001';
```

### Licença vencida

```sql
UPDATE licensing.licenses
SET expires_at = CURRENT_DATE - INTERVAL '1 day', status = 'active'
WHERE license_key = 'BOXIO-2026-CLIENTE001';
```

Restaurar:

```sql
UPDATE licensing.licenses
SET expires_at = '2027-05-18', status = 'active'
WHERE license_key = 'BOXIO-2026-CLIENTE001';
```

### Limite de dispositivos

```sql
UPDATE licensing.licenses
SET max_devices = 1
WHERE license_key = 'BOXIO-2026-CLIENTE001';
```

## 20. Comandos úteis

```bash
sudo docker ps
sudo docker logs -f boxio-license-server
cd /opt/boxio-license-server && sudo docker compose restart
cd /opt/boxio-license-server && sudo docker compose up -d --build
curl http://127.0.0.1:8000/health
curl https://licenses.seudominio.com/health
sudo nginx -t
sudo systemctl status nginx
sudo certbot renew --dry-run
```

## 21. Erros comuns

### 502 Bad Gateway

FastAPI ou Docker está parado:

```bash
sudo docker ps
sudo docker logs -f boxio-license-server
curl http://127.0.0.1:8000/health
```

### Certbot falhou

Verifique:

```bash
sudo ufw status
sudo nginx -t
ping licenses.seudominio.com
```

### Boxio não valida licença

Verifique:

```env
BOXIO_LICENSE_SERVER_URL=https://licenses.seudominio.com
```

### Neon não conecta

Verifique:

```text
DATABASE_URL correta
sslmode=require
senha correta
permissões no schema licensing
```

## 22. Checklist final

```text
[ ] DNS licenses.seudominio.com aponta para VPS
[ ] VPS atualizada
[ ] Firewall libera 22, 80, 443
[ ] Docker instalado
[ ] license_server em /opt/boxio-license-server
[ ] .env de produção criado
[ ] Docker container rodando
[ ] curl http://127.0.0.1:8000/health funciona
[ ] Nginx configurado
[ ] Certbot gerou HTTPS
[ ] curl https://licenses.seudominio.com/health funciona
[ ] Boxio Desktop usa BOXIO_LICENSE_SERVER_URL=https://licenses.seudominio.com
[ ] Licença real criada
[ ] Ativação aparece em licensing.device_activations
[ ] Eventos aparecem em licensing.license_events
[ ] Revogação bloqueia
[ ] Vencimento bloqueia
[ ] Limite de dispositivos bloqueia
```
