# Servidor de licenças — referência de implementação

O Boxio v1.21 já possui o cliente de licenciamento no desktop. Para produção, você precisará publicar um servidor HTTPS com três endpoints:

- `POST /licenses/activate`
- `POST /licenses/validate`
- `POST /licenses/deactivate`

Você pode implementar com:

- FastAPI em Render/Railway/Fly.io;
- Supabase Edge Functions;
- Cloudflare Workers;
- servidor próprio;
- API interna com acesso ao PostgreSQL/Neon.

## Regras mínimas do servidor

1. Buscar `license_key` em `boxio.app_licenses`.
2. Verificar se:
   - licença existe;
   - está ativa;
   - não venceu;
   - não ultrapassou `max_devices`.
3. Criar ou atualizar registro em `boxio.device_activations`.
4. Retornar `activation_id` e `token`.
5. Na validação, conferir:
   - chave;
   - token;
   - dispositivo;
   - status;
   - validade.
6. Se licença estiver vencida, revogada ou bloqueada, retornar `ok=false`.

## Tabelas já previstas

O schema atual já possui:

- `app_licenses`
- `device_activations`

Para uma versão mais avançada, recomenda-se adicionar:

- status textual;
- token hash;
- revoked_at;
- activation logs;
- license plans;
- audit trail.

