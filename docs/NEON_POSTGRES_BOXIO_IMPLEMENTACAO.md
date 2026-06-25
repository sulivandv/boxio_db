# Boxio + Neon PostgreSQL: implementação integrada no projeto

Este documento descreve o que foi integrado ao Boxio v1.18.0 para usar PostgreSQL hospedado no Neon.

## 1. O que foi alterado no projeto

- A configuração PostgreSQL agora aceita `BOXIO_DATABASE_URL`, no formato copiado do Neon.
- A conexão usa `sslmode=require`, obrigatório no Neon.
- O schema padrão é `boxio`, configurado por `BOXIO_DB_SCHEMA=boxio`.
- Foi criado o arquivo SQL oficial `src/database/sql/schema_neon_boxio.sql`.
- Foi criado o inicializador `src/database/postgres/init_db.py`.
- Foi criado o teste `test_neon_connection.py`.
- A migração JSON para PostgreSQL foi ajustada para ser executada por linha de comando e evitar duplicidade por SKU.
- O sistema mantém o JSON local como backup/fallback até a migração ser validada.

## 2. Arquivos importantes

```text
.env                                      # credenciais reais, não enviar ao GitHub
config/examples/.env.neon.example         # modelo seguro sem senha real
src/database/sql/schema_neon_boxio.sql    # cria schema e tabelas no Neon
src/database/postgres/config.py           # lê variáveis de ambiente
src/database/postgres/connection.py       # cria engine e sessões SQLAlchemy
src/database/postgres/init_db.py          # executa schema SQL no banco
src/database/migrations/json_to_postgres.py # migra JSON para PostgreSQL
test_neon_connection.py                   # testa a conexão
```

## 3. Passo a passo após conectar o pgAdmin

### 3.1 Criar o arquivo `.env`

Na raiz do projeto, copie:

```text
config/examples/.env.neon.example
```

para:

```text
.env
```

Edite `SUA_SENHA_AQUI` com a senha real do Neon.

### 3.2 Instalar dependências

```bash
pip install -r requirements.txt
```

### 3.3 Testar conexão Python -> Neon

```bash
python test_neon_connection.py
```

Resultado esperado:

```text
Conexão realizada com sucesso!
Banco: neondb
Usuário: neondb_owner
Schema atual: boxio ou public
```

Se o schema ainda aparecer como `public`, não é erro. Ele será criado no próximo passo.

### 3.4 Criar schema e tabelas pelo Python

```bash
python -m src.database.postgres.init_db
```

Esse comando executa `schema_neon_boxio.sql` e cria todas as tabelas necessárias.

### 3.5 Conferir no pgAdmin

No Query Tool, rode:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'boxio'
ORDER BY table_name;
```

Você deve ver tabelas como `products`, `categories`, `stock_movements`, `purchase_requests`, `audit_logs`.

## 4. Migração do JSON para o Neon

Antes de migrar, faça backup do JSON:

```bash
copy database\inventory_db.json database\inventory_db_backup_antes_neon.json
```

Depois rode:

```bash
python -m src.database.migrations.json_to_postgres --json database/inventory_db.json --company "Inovi"
```

O script cria categorias, marcas, fornecedores, produtos e histórico de fornecedor.

## 5. Host principal x Pooler

Use o host principal para:

- pgAdmin;
- criação de tabelas;
- migração JSON;
- backup/restore;
- debugging.

Use o pooler futuramente para:

- o aplicativo Boxio em vários computadores simultâneos.

Para ativar pooler no app:

```env
BOXIO_DB_USE_POOLER=true
```

## 6. Segurança

- Nunca envie `.env` para o GitHub.
- Use SSL: `sslmode=require`.
- Comece com `neondb_owner`, mas futuramente crie uma role específica `boxio_app`.
- Faça backup antes de qualquer migração.
- Use transações curtas nas movimentações de estoque.

## 7. Próximos passos recomendados

1. Validar conexão via pgAdmin.
2. Rodar `python test_neon_connection.py`.
3. Rodar `python -m src.database.postgres.init_db`.
4. Conferir tabelas no pgAdmin.
5. Migrar JSON.
6. Testar em dois computadores.
7. Só então ativar pooler.


## 8. Scripts auxiliares Windows

Também foram adicionados scripts PowerShell para facilitar:

```powershell
.	ools
eon\setup_neon_database.ps1
.	ools
eon\migrate_json_to_neon.ps1
```

Use o primeiro para testar conexão e criar tabelas. Use o segundo para migrar o JSON depois que o banco estiver validado.
