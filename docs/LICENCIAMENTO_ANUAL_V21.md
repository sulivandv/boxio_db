# Boxio v1.21 — Sistema de licenciamento anual

## Objetivo

Esta versão adiciona uma base comercial de licenciamento anual para proteger o uso do sistema após empacotamento com PyInstaller.

O cliente recebe somente o direito de uso do executável. O código-fonte e a titularidade intelectual permanecem com o desenvolvedor.

## Fluxo implementado

1. O sistema inicia.
2. O `LicenseManager` verifica se existe licença local.
3. Se não houver licença ou se ela estiver inválida, o sistema abre a tela de ativação.
4. A ativação envia ao servidor:
   - chave de licença;
   - empresa;
   - fingerprint do dispositivo;
   - nome do dispositivo;
   - versão instalada.
5. O servidor deve responder com:
   - `ok`;
   - `status`;
   - `license_key`;
   - `activation_id`;
   - `token`;
   - `expires_at`;
   - `plan`;
   - `max_users`;
   - `max_devices`;
   - `allowed_modules`.
6. O Boxio salva os dados localmente em `AppData/Boxio/Config/license.json`.
7. Em próximas aberturas, o sistema valida a licença local e faz checagem online periódica.
8. Caso esteja vencida, revogada ou bloqueada, o acesso é interrompido.

## Variáveis de ambiente

Configure no `.env`:

```env
BOXIO_LICENSE_SERVER_URL=https://seu-servidor.com.br/boxio
BOXIO_LICENSE_OFFLINE_GRACE_DAYS=7
BOXIO_LICENSE_TIMEOUT=12
```

## Endpoints esperados

### POST `/licenses/activate`

Entrada:

```json
{
  "license_key": "BOXIO-2026-XXXX",
  "company_name": "Empresa Cliente",
  "device_fingerprint": "hash_sha256",
  "device_name": "PC-RECEPCAO",
  "app_version": "1.21.0",
  "platform": "nt"
}
```

Resposta esperada:

```json
{
  "ok": true,
  "status": "active",
  "message": "Licença ativada.",
  "license_key": "BOXIO-2026-XXXX",
  "activation_id": "uuid",
  "token": "token-assinado-pelo-servidor",
  "company_id": "uuid",
  "company_name": "Empresa Cliente",
  "plan": "profissional",
  "expires_at": "2027-05-18",
  "max_users": 5,
  "max_devices": 5,
  "allowed_modules": ["inventory", "purchases", "reports"]
}
```

### POST `/licenses/validate`

Valida se a licença continua ativa, não expirada e não revogada.

### POST `/licenses/deactivate`

Endpoint futuro para desativar uma máquina e liberar ativação em outro dispositivo.

## Regras comerciais suportadas

- licença anual;
- vencimento automático;
- ativação vinculada a dispositivo;
- limite de ativações por licença;
- validação online;
- tolerância offline limitada;
- status de revogação/bloqueio;
- planos e módulos;
- preparação para filiais e múltiplos usuários.

## Observações de segurança

Nenhum sistema de licenciamento client-side é inviolável. Esta versão implementa uma base comercial adequada para distribuição inicial, mas em produção recomenda-se:

- usar HTTPS obrigatório;
- assinar instaladores;
- não expor segredos no cliente;
- validar tudo no servidor;
- registrar logs de ativação e validação;
- limitar ativações por licença;
- usar ofuscação básica no executável;
- manter verificação periódica online;
- usar backup e rollback nas atualizações.
