# Boxio v2.2.3 — Correção definitiva da validação de licenças

## Problema corrigido

Foi identificado que o Boxio podia abrir normalmente após uma licença ser revogada no banco, quando a validação local ainda estava dentro do período de cache definido por `next_online_check`.

## Causa

A validação de inicialização usava cache local e só consultava o servidor quando `next_online_check` vencia. Assim, uma licença revogada no servidor podia continuar abrindo até a próxima checagem programada.

## Correções aplicadas

### Desktop

- `ensure_valid()` agora força validação online antes de liberar acesso ao sistema.
- Estados inválidos retornados pelo servidor agora bloqueiam sempre:
  - `revoked`
  - `blocked`
  - `expired`
  - `cancelled`
  - `inactive`
  - `suspended`
  - `device_revoked`
  - `device_mismatch`
  - `activation_not_found`
  - `invalid_token`
  - `not_found`
  - `device_limit`
- A tolerância offline só é aplicada em falhas reais de comunicação:
  - `network_error`
  - timeout
  - erro HTTP 5xx
  - HTTP 429
- Caso o servidor responda que a licença é inválida, revogada ou expirada, o acesso é bloqueado imediatamente e o status local é atualizado.

### Servidor de licenças

- Status da licença agora é normalizado em minúsculas.
- Licenças com `revoked_at` preenchido são sempre bloqueadas.
- Licenças com status `revoked`, `blocked`, `cancelled`, `inactive` ou `suspended` são bloqueadas.
- Licenças vencidas atualizam status para `expired` e bloqueiam.
- Validação agora também verifica limite de dispositivos, protegendo o caso em que `max_devices` foi reduzido depois de ativações já realizadas.

## Testes manuais recomendados

### 1. Testar licença revogada

```sql
UPDATE licensing.licenses
SET status = 'revoked', revoked_at = now()
WHERE license_key = 'BOXIO-2026-0001';
```

Resultado esperado:

- O Boxio não deve abrir.
- Deve exibir mensagem de licença revogada/bloqueada.

Para restaurar:

```sql
UPDATE licensing.licenses
SET status = 'active', revoked_at = NULL
WHERE license_key = 'BOXIO-2026-0001';
```

### 2. Testar licença vencida

```sql
UPDATE licensing.licenses
SET expires_at = CURRENT_DATE - INTERVAL '1 day', status = 'active'
WHERE license_key = 'BOXIO-2026-0001';
```

Resultado esperado:

- O servidor deve retornar `expired`.
- O Boxio deve bloquear o acesso.

Para restaurar:

```sql
UPDATE licensing.licenses
SET expires_at = '2027-05-18', status = 'active', revoked_at = NULL
WHERE license_key = 'BOXIO-2026-0001';
```

### 3. Testar limite de dispositivos

Para impedir novos dispositivos:

```sql
UPDATE licensing.licenses
SET max_devices = 1
WHERE license_key = 'BOXIO-2026-0001';
```

Se já houver mais de um dispositivo ativo, somente o primeiro dispositivo ativo continuará autorizado; os demais serão bloqueados com `device_limit`.

Consultar dispositivos:

```sql
SELECT id, device_name, status, activated_at, last_validation_at
FROM licensing.device_activations
ORDER BY activated_at ASC;
```

### 4. Ver logs de validação

```sql
SELECT event_type, event_status, message, device_name, created_at
FROM licensing.license_events
ORDER BY created_at DESC
LIMIT 50;
```

## Versão

Boxio v2.2.3
