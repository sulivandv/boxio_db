# Boxio v2.2.0 — Arquitetura com servidor de licenças

## Visão geral

Esta versão adiciona ao projeto um servidor backend separado para licenciamento anual do Boxio, mantendo as tecnologias já usadas no projeto:

- Python
- FastAPI
- PostgreSQL/Neon
- SQLAlchemy
- `.env`
- GitHub Releases
- PyInstaller no desktop

## Estrutura adicionada

```text
license_server/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   ├── routers/
│   │   ├── licenses.py
│   │   ├── releases.py
│   │   └── admin.py
│   └── services/
│       └── license_service.py
├── scripts/
│   └── create_license.py
├── sql/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Fluxo de ativação

1. Cliente instala o Boxio Desktop.
2. O Boxio solicita a chave de licença.
3. O desktop envia a chave, fingerprint da máquina, nome do dispositivo e versão.
4. O servidor valida a licença no PostgreSQL/Neon.
5. Se a licença estiver ativa, dentro do prazo e com limite de dispositivos disponível:
   - registra o dispositivo;
   - gera token assinado;
   - salva hash do token no servidor;
   - retorna token ao desktop.
6. O desktop salva os dados localmente em AppData.
7. Periodicamente, o desktop valida online o status da licença.

## Endpoints implementados

Compatíveis com o desktop atual:

- `POST /licenses/activate`
- `POST /licenses/validate`
- `POST /licenses/deactivate`

Aliases futuros:

- `POST /api/license/activate`
- `POST /api/license/validate`
- `POST /api/license/heartbeat`
- `POST /api/license/revoke`
- `GET /api/releases/latest`

## Configuração no desktop

Local:

```env
BOXIO_LICENSE_SERVER_URL=http://127.0.0.1:8000
```

Produção:

```env
BOXIO_LICENSE_SERVER_URL=https://seu-servidor-de-licencas.com
```

## Segurança

- O banco nunca é acessado diretamente pelo desktop para licenciamento.
- O desktop conversa apenas com a API HTTPS.
- O token é assinado com HMAC SHA-256.
- O servidor salva apenas hash do token.
- Cada ativação é vinculada ao fingerprint do dispositivo.
- O servidor registra eventos de ativação, validação e revogação.
- Licenças vencidas, revogadas ou bloqueadas são recusadas.

## Próximas evoluções recomendadas

- painel administrativo web;
- autenticação administrativa;
- integração com Stripe/PayPal/Mercado Pago;
- controle de inadimplência;
- atualização obrigatória por versão mínima;
- assinatura digital do instalador;
- ofuscação adicional no build PyInstaller.
