# Boxio v1.19.0 — integração online PostgreSQL/Neon

Esta versão torna o PostgreSQL/Neon a fonte principal de dados quando o arquivo `.env` estiver configurado com:

```env
BOXIO_DB_MODE=postgresql
BOXIO_DB_SCHEMA=boxio
BOXIO_DATABASE_URL=postgresql+psycopg://usuario:senha@host/neondb?sslmode=require
```

## O que mudou

- `src/services/stock_service.py` continua sendo o ponto de entrada usado pela interface.
- Quando `BOXIO_DB_MODE=postgresql`, ele carrega `StockServicePostgres`.
- Quando `BOXIO_DB_MODE` não estiver configurado ou estiver como `json`, o sistema mantém o JSON como fallback temporário.
- Novos cadastros, edições, exclusões, movimentações e compras passam a ser gravados no PostgreSQL/Neon.
- O JSON não deve mais ser usado como base principal em produção.

## Arquivos principais

```text
src/services/stock_service.py
src/services/stock_service_postgres.py
src/database/postgres/config.py
src/database/postgres/connection.py
src/database/sql/schema_neon_boxio.sql
```

## Teste recomendado

1. Abra o Boxio com `.env` apontando para Neon.
2. Cadastre um item chamado `Teste Neon`.
3. No pgAdmin, execute:

```sql
SELECT sku, name, current_stock
FROM boxio.products
WHERE name ILIKE '%Teste Neon%' OR sku ILIKE '%TESTE%';
```

Se aparecer no pgAdmin, o sistema está gravando online.

## Ajuda contextual

A interface recebeu o componente `HelpIcon`, exibido como `ℹ️`. Ele aparece em títulos, seções e pontos estratégicos da interface para substituir tooltips invisíveis por ajuda visual e padronizada.
