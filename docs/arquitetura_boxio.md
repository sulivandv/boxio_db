# Arquitetura técnica do Boxio

## Camadas

1. **UI desktop**: PySide/PyQt.
2. **Serviços de aplicação**: regras de estoque, compras, fornecedores e relatórios.
3. **Persistência**: JSON local legado e PostgreSQL empresarial.
4. **Atualizador**: GitHub Releases, manifesto, SHA-256 e logs.
5. **Licenciamento**: licença local e preparação para validação online.

## Diretórios persistentes

Todos os caminhos ficam em `src/core/paths.py`.

- Dados: `AppData/Local/Boxio/Data`
- Configurações: `AppData/Local/Boxio/Config`
- Logs: `AppData/Local/Boxio/Logs`
- Cache de atualização: `AppData/Local/Boxio/Cache/updates`

## PostgreSQL

O schema principal está em:

```text
src/database/sql/schema_postgresql.sql
```

Ele cobre empresas, usuários, permissões, produtos, categorias, marcas, fornecedores, locais, unidades, movimentações, compras, histórico de fornecedores, auditoria, licenças e dispositivos.

## Atualizações

Módulos principais:

- `src/updater/github_releases.py`
- `src/updater/update_checker.py`
- `src/updater/downloader.py`
- `src/updater/verifier.py`
- `src/updater/update_manager.py`

O fluxo usa GitHub Releases, baixa `latest.json`, valida versão, baixa pacote e confere SHA-256.


## Atualização v1.18.0 - Neon PostgreSQL

O projeto agora inclui `schema_neon_boxio.sql`, `init_db.py`, `.env.neon.example` e `test_neon_connection.py` para configuração direta com Neon. Use o host principal para pgAdmin/migração e o pooler apenas depois de validar o uso multiusuário.
