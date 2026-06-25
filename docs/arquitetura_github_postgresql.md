# Arquitetura v15 — GitHub Releases + PostgreSQL Multiusuário

## 1. Objetivo

Esta versão prepara o Boxio para operar como software desktop empresarial em PySide/PyQt com:

- distribuição gratuita de atualizações via GitHub Releases;
- preservação dos dados do cliente durante atualizações;
- banco PostgreSQL centralizado para 5 a 10 computadores simultâneos;
- migração dos dados JSON legados para SQL;
- base para licença anual empresarial;
- arquitetura mais escalável para novos módulos.

## 2. Separação de responsabilidades

A aplicação desktop fica instalada em uma pasta do sistema ou em uma pasta escolhida pelo usuário. Dados, configurações, licença, cache, logs e downloads ficam no perfil do usuário por meio do módulo `src/core/paths.py`.

```text
Arquivos do sistema:
C:\Program Files\Boxio\

Dados persistentes do cliente:
C:\Users\<usuario>\AppData\Local\Boxio\

Configurações e licença:
C:\Users\<usuario>\AppData\Local\Boxio\Config\

Logs:
C:\Users\<usuario>\AppData\Local\Boxio\Logs\
```

Essa separação evita que uma atualização substitua dados do cliente.

## 3. Nova estrutura de pastas

```text
src/
├── core/
│   ├── paths.py              # diretórios persistentes
│   ├── version.py            # versão do app, schema e GitHub Releases
│   ├── backup.py             # backup antes de atualização/migração
│   └── logger.py             # logs de app e update
│
├── database/
│   ├── postgres/
│   │   ├── config.py         # credenciais via ambiente/.env
│   │   ├── connection.py     # engine, pool e sessões SQLAlchemy
│   │   ├── models.py         # modelos ORM
│   │   └── repositories.py   # operações transacionais
│   │
│   ├── migrations/
│   │   └── json_to_postgres.py
│   │
│   └── sql/
│       └── schema_postgresql.sql
│
├── updater/
│   ├── github_releases.py    # consulta API gratuita do GitHub
│   ├── update_checker.py     # detecta nova versão
│   ├── downloader.py         # baixa pacote
│   ├── verifier.py           # valida SHA-256
│   └── update_manager.py     # orquestra backup/download/instalação
│
└── licensing/
    └── license_manager.py    # base para licença anual
```

## 4. Atualização via GitHub Releases

O fluxo usa apenas recursos gratuitos:

1. O desenvolvedor gera um build `.zip` ou `.exe`.
2. Gera o arquivo `latest.json` com SHA-256.
3. Publica uma release no GitHub com a tag `v1.18.0`.
4. Anexa `latest.json` e o pacote da versão como assets.
5. O app consulta a API pública `https://api.github.com/repos/<owner>/<repo>/releases/latest`.
6. O app baixa `latest.json`.
7. O app compara a versão remota com `APP_VERSION`.
8. Se houver atualização, mostra uma notificação na interface.
9. O usuário baixa/instala manualmente ou aciona o fluxo automático com `updater.exe`.
10. O pacote é validado por SHA-256 antes de instalar.

## 5. Exemplo de latest.json

```json
{
  "product": "boxio",
  "channel": "stable",
  "latest_version": "1.18.0",
  "minimum_supported_version": "1.14.0",
  "db_schema_version": 15,
  "download_url": "",
  "sha256": "HASH_DO_PACOTE",
  "mandatory": false,
  "notes": ["Correções e melhorias"]
}
```

Quando `download_url` fica vazio, o app tenta localizar automaticamente o asset `.zip` ou `.exe` na release.

## 6. PostgreSQL multiusuário

Para 5 a 10 computadores simultâneos, o recomendado é PostgreSQL em uma máquina central ou servidor gratuito/barato. O desktop conecta nesse banco com usuário restrito.

Boas práticas:

- criar usuário PostgreSQL exclusivo para o app;
- não usar usuário `postgres` no cliente desktop;
- usar senha forte;
- usar `sslmode=prefer` ou `require` se for acesso remoto;
- limitar acesso por firewall/IP;
- usar pool de conexões pequeno;
- usar transações em todas as movimentações de estoque;
- usar `SELECT FOR UPDATE` ao alterar saldo de produto.

## 7. Migração JSON para SQL

A migração é feita pelo script:

```text
src/database/migrations/json_to_postgres.py
```

Ele lê o JSON legado, cria cadastros auxiliares e insere produtos com histórico de fornecedores. O JSON original não é apagado.

## 8. Compatibilidade entre versões

- `APP_VERSION` controla versão do executável.
- `DB_SCHEMA_VERSION` controla versão do banco.
- Alterações no banco devem ser feitas por migrações numeradas.
- Antes de atualizar, o app cria backup automático dos dados locais.
- Atualizações incompatíveis podem ser marcadas como obrigatórias no `latest.json`.

## 9. Licenciamento anual

A versão mantém estrutura para licença anual. O arquivo local `license.json` pode guardar:

- chave da licença;
- cliente;
- validade;
- plano contratado;
- limite de usuários/dispositivos;
- módulos habilitados.

No futuro, essa validação pode consultar uma API gratuita/baixo custo, como Supabase, Cloudflare Worker ou servidor próprio.


## Atualização v1.18.0 - Neon PostgreSQL

O projeto agora inclui `schema_neon_boxio.sql`, `init_db.py`, `.env.neon.example` e `test_neon_connection.py` para configuração direta com Neon. Use o host principal para pgAdmin/migração e o pooler apenas depois de validar o uso multiusuário.
