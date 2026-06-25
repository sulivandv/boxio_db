# Boxio — Guia completo para iniciantes

Este guia explica como transformar o projeto Boxio em um sistema desktop empresarial com PySide/PyQt, PostgreSQL, GitHub Releases, atualização contínua, licenciamento anual e operação multiusuário.

> Objetivo: permitir que uma pessoa que nunca usou PostgreSQL, GitHub Releases, deploy desktop ou atualização automática consiga configurar, rodar, empacotar e evoluir o Boxio com segurança.

---

## 1. Visão geral do Boxio

**Boxio** é o nome oficial do sistema. A partir desta versão, todos os caminhos, títulos, executável, logs, configurações, banco e atualizador passam a usar essa identidade.

O Boxio é dividido em quatro grandes partes:

1. **Aplicativo desktop**: interface em PySide/PyQt, instalada em cada computador.
2. **Banco de dados PostgreSQL**: banco central acessado por todos os computadores.
3. **Atualização via GitHub Releases**: canal gratuito para publicar novas versões.
4. **Licenciamento anual**: estrutura preparada para validar permissões, plano, validade e dispositivos.

---

## 2. Estrutura profissional de pastas

```text
boxio_v16/
├── main.py
├── requirements.txt
├── README.md
│
├── assets/
│   ├── logo.png
│   └── README_LOGO.txt
│
├── config/
│   └── examples/
│       └── .env.example
│
├── database/
│   └── inventory_db.json
│
├── docs/
│   ├── GUIA_COMPLETO_BOXIO_INICIANTE.md
│   ├── arquitetura_github_postgresql.md
│   ├── schema_sqlite.sql
│   └── api_contract.md
│
├── releases/
│   └── latest.json
│
├── src/
│   ├── core/
│   │   ├── paths.py
│   │   ├── version.py
│   │   ├── backup.py
│   │   └── logger.py
│   │
│   ├── database/
│   │   ├── postgres/
│   │   │   ├── config.py
│   │   │   ├── connection.py
│   │   │   ├── models.py
│   │   │   └── repositories.py
│   │   ├── migrations/
│   │   │   ├── json_to_postgres.py
│   │   │   ├── migration_014_update_infra.py
│   │   │   └── migration_016_boxio_identity.py
│   │   └── sql/
│   │       └── schema_postgresql.sql
│   │
│   ├── licensing/
│   │   └── license_manager.py
│   │
│   ├── updater/
│   │   ├── github_releases.py
│   │   ├── update_checker.py
│   │   ├── downloader.py
│   │   ├── verifier.py
│   │   ├── update_manager.py
│   │   └── update_dialog.py
│   │
│   ├── services/
│   ├── domain/
│   └── ui/
│
└── tools/
    ├── build_release.md
    └── release/
        ├── create_windows_build.ps1
        └── build_github_release.py
```

---

## 3. Separação entre sistema e dados do cliente

Nunca salve dados importantes dentro da pasta onde o `.exe` fica instalado.

### Arquivos da aplicação

Ficam na pasta de instalação:

```text
C:\Program Files\Boxio\
├── Boxio.exe
├── _internal\
├── assets\
└── database\inventory_db.json  # modelo inicial, não é o banco vivo do cliente
```

### Dados persistentes do cliente

Ficam no perfil do usuário:

```text
C:\Users\<usuario>\AppData\Local\Boxio\
├── Data\database\inventory_db.json
├── Data\backups\
├── Data\exports\
├── Data\tmp\
├── Config\settings.json
├── Config\license.json
├── Config\version.json
├── Cache\updates\
└── Logs\app.log / update.log
```

O arquivo `src/core/paths.py` centraliza todos esses caminhos. Se um dia você mudar de Windows para Linux ou macOS, a biblioteca `platformdirs` ajusta os diretórios automaticamente.

---

## 4. Instalação do ambiente Python

### 4.1 Instalar Python

1. Acesse `python.org`.
2. Baixe a versão estável do Python 3.12 ou 3.13.
3. Durante a instalação, marque **Add Python to PATH**.
4. Depois abra o PowerShell e teste:

```powershell
python --version
pip --version
```

### 4.2 Criar ambiente virtual

Na pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Quando ativado, o terminal deve mostrar `(.venv)` no início da linha.

### 4.3 Instalar dependências

```powershell
pip install -r requirements.txt
```

Principais dependências:

- `PySide6`: interface gráfica.
- `openpyxl`: exportação Excel.
- `platformdirs`: diretórios corretos do usuário.
- `packaging`: comparação de versões.
- `SQLAlchemy`: camada SQL.
- `psycopg[binary]`: driver PostgreSQL.
- `python-dotenv`: leitura de `.env`.

---

## 5. PostgreSQL explicado de forma prática

PostgreSQL é um banco de dados relacional. Ele será o centro dos dados do Boxio quando houver 5 a 10 computadores usando o sistema ao mesmo tempo.

Em vez de cada computador ter um JSON separado, todos acessam o mesmo banco:

```text
Computador 1 ┐
Computador 2 ├──> PostgreSQL central ──> estoque, compras, usuários, logs
Computador 3 ┘
```

### 5.1 Instalar PostgreSQL e pgAdmin no Windows

1. Baixe o instalador em `postgresql.org`.
2. Execute o instalador.
3. Marque PostgreSQL Server e pgAdmin.
4. Defina uma senha para o usuário `postgres`.
5. Use a porta padrão `5432`.
6. Finalize a instalação.

### 5.2 Criar banco Boxio pelo pgAdmin

1. Abra o pgAdmin.
2. Conecte no servidor local.
3. Clique com botão direito em **Databases**.
4. Escolha **Create > Database**.
5. Nome: `boxio`.
6. Salve.

### 5.3 Criar usuário do sistema

No pgAdmin, abra Query Tool e rode:

```sql
CREATE USER boxio_app WITH PASSWORD 'troque_esta_senha';
CREATE DATABASE boxio OWNER boxio_app;
GRANT ALL PRIVILEGES ON DATABASE boxio TO boxio_app;
```

Se o banco já existir:

```sql
ALTER DATABASE boxio OWNER TO boxio_app;
GRANT ALL PRIVILEGES ON DATABASE boxio TO boxio_app;
```

### 5.4 Criar tabelas do Boxio

No terminal:

```powershell
psql -U boxio_app -d boxio -f src/database/sql/schema_postgresql.sql
```

Ou pelo pgAdmin:

1. Abra o banco `boxio`.
2. Abra **Query Tool**.
3. Cole o conteúdo de `src/database/sql/schema_postgresql.sql`.
4. Execute.

### 5.5 Configurar `.env`

Copie:

```text
config/examples/.env.example
```

Para:

```text
.env
```

Edite:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=boxio
POSTGRES_USER=boxio_app
POSTGRES_PASSWORD=troque_esta_senha
POSTGRES_SSLMODE=prefer
```

### 5.6 Testar conexão

No Python:

```python
from src.database.postgres.connection import engine

with engine.connect() as conn:
    print(conn.exec_driver_sql("SELECT version()").scalar())
```

Se aparecer a versão do PostgreSQL, a conexão está funcionando.

---

## 6. Liberar acesso remoto ao PostgreSQL

Para outros computadores acessarem o banco, o PostgreSQL precisa aceitar conexões externas.

### 6.1 Editar `postgresql.conf`

Procure:

```text
listen_addresses = 'localhost'
```

Troque por:

```text
listen_addresses = '*'
```

### 6.2 Editar `pg_hba.conf`

Adicione uma regra para sua rede local:

```text
host    boxio    boxio_app    192.168.0.0/24    scram-sha-256
```

A faixa pode mudar conforme sua rede. Exemplos comuns:

```text
192.168.0.0/24
192.168.1.0/24
10.0.0.0/24
```

### 6.3 Liberar firewall do Windows

Libere a porta `5432` para entrada no computador/servidor onde o PostgreSQL está instalado.

### 6.4 Reiniciar PostgreSQL

No Windows Services, reinicie o serviço PostgreSQL.

---

## 7. Multiusuário: como evitar conflitos

Quando 5 a 10 usuários movimentam estoque, o risco é duas pessoas alterarem o mesmo item ao mesmo tempo.

A solução é usar transações e bloqueio de linha.

Exemplo conceitual:

```sql
BEGIN;
SELECT * FROM products WHERE id = :id FOR UPDATE;
UPDATE products SET current_stock = current_stock - 1 WHERE id = :id;
INSERT INTO stock_movements (...);
COMMIT;
```

`FOR UPDATE` bloqueia aquele produto durante a movimentação. Assim, outro usuário espera a transação terminar antes de mexer no mesmo estoque.

Boas práticas:

- Sempre registrar movimentação.
- Nunca alterar estoque diretamente sem histórico.
- Usar transação para entrada, saída, ajuste e recebimento de compra.
- Validar se há saldo suficiente antes de saída.
- Registrar usuário, data/hora e origem da ação.

---

## 8. Migração de JSON para PostgreSQL

A migração deve acontecer uma vez, em ambiente controlado.

### 8.1 Estratégia

1. Fazer backup do JSON atual.
2. Criar o banco PostgreSQL.
3. Criar tabelas com `schema_postgresql.sql`.
4. Ler `inventory_db.json`.
5. Inserir categorias, marcas, fornecedores e locais.
6. Inserir produtos.
7. Inserir movimentações, compras, histórico comercial e auditoria.
8. Validar contagens.
9. Testar o Boxio apontando para PostgreSQL.

### 8.2 Comando sugerido

```powershell
python src/database/migrations/json_to_postgres.py --json database/inventory_db.json
```

### 8.3 Cuidados

- Não apague o JSON original.
- Faça backup antes.
- Migre primeiro para um banco de teste.
- Confira se o total de produtos bate com o sistema antigo.
- Só depois use em produção.

---

## 9. GitHub Releases para atualizações gratuitas

GitHub Releases permite publicar versões do Boxio sem pagar hospedagem.

### 9.1 Criar conta

1. Acesse GitHub.
2. Crie sua conta.
3. Confirme email.

### 9.2 Criar repositório

Sugestão:

```text
boxio-releases
```

Ele pode ser público no começo. Se for privado, a atualização exigirá token/API e ficará mais complexa.

### 9.3 Configurar o projeto

No arquivo `src/core/version.py`, ajuste:

```python
GITHUB_OWNER = "seu_usuario"
GITHUB_REPO = "boxio-releases"
```

Ou use `.env`:

```env
GITHUB_OWNER=seu_usuario
GITHUB_REPO=boxio-releases
GITHUB_CHANNEL=stable
```

### 9.4 Criar uma release

1. Entre no repositório `boxio-releases`.
2. Clique em **Releases**.
3. Clique em **Draft a new release**.
4. Tag: `v1.18.0`.
5. Título: `Boxio v1.18.0`.
6. Anexe:
   - `boxio_1.18.0.zip`
   - `latest.json`
7. Publique.

O Boxio consulta:

```text
https://api.github.com/repos/SEU_USUARIO/boxio-releases/releases/latest
```

Depois baixa o `latest.json` anexado à release.

---

## 10. Estrutura do `latest.json`

```json
{
  "product": "boxio",
  "channel": "stable",
  "latest_version": "1.18.0",
  "minimum_supported_version": "1.15.0",
  "db_schema_version": 16,
  "mandatory": false,
  "download_url": "https://github.com/SEU_USUARIO/boxio-releases/releases/download/v1.18.0/boxio_1.18.0.zip",
  "installer_url": "https://github.com/SEU_USUARIO/boxio-releases/releases/download/v1.18.0/BoxioSetup_1.18.0.exe",
  "sha256": "HASH_DO_ARQUIVO",
  "notes": [
    "Correções e melhorias do Boxio"
  ]
}
```

O campo `sha256` impede instalação de arquivo corrompido ou modificado.

---

## 11. Atualização sem perda de dados

O Boxio preserva dados porque:

- O executável fica separado dos dados.
- O banco local fica em AppData/Boxio.
- PostgreSQL fica em servidor central.
- Antes de atualizar, o sistema cria backup.
- O pacote baixado é validado com SHA-256.
- Migrações são versionadas.

Fluxo ideal:

```text
1. Boxio abre
2. Verifica GitHub Releases
3. Detecta versão nova
4. Mostra aviso na interface
5. Usuário escolhe atualizar
6. Sistema baixa pacote
7. Valida SHA-256
8. Cria backup
9. Executa instalador/updater
10. Reabre na versão nova
11. Executa migrações pendentes
```

---

## 12. Empacotamento com PyInstaller

### 12.1 Instalar PyInstaller

```powershell
pip install pyinstaller
```

### 12.2 Gerar build manual

```powershell
pyinstaller --noconfirm --clean --windowed --name Boxio --add-data "assets;assets" --add-data "database;database" main.py
```

Resultado:

```text
dist/Boxio/Boxio.exe
```

### 12.3 Gerar ZIP de release

```powershell
Compress-Archive -Path "dist\Boxio\*" -DestinationPath "dist\boxio_1.18.0.zip" -Force
```

### 12.4 Gerar `latest.json`

```powershell
python tools\release\build_github_release.py "dist\boxio_1.18.0.zip" "1.18.0"
```

Esse script calcula automaticamente o SHA-256 e gera `dist/latest.json`.

---

## 13. Criar instalador Windows

Para começar, você pode distribuir ZIP.

Depois, pode usar ferramentas gratuitas como:

- Inno Setup
- NSIS

Estrutura recomendada para instalador:

```text
C:\Program Files\Boxio\
├── Boxio.exe
├── updater.exe
├── assets\
└── _internal\
```

Não coloque banco de produção nessa pasta.

---

## 14. Backups do PostgreSQL

### 14.1 Backup

```powershell
pg_dump -U boxio_app -h localhost -d boxio -F c -f backup_boxio.dump
```

### 14.2 Restauração

```powershell
pg_restore -U boxio_app -h localhost -d boxio -c backup_boxio.dump
```

Para cliente empresarial, faça backup automático diário.

---

## 15. Hospedagem gratuita ou barata do PostgreSQL

Opções para começar:

1. **Servidor local na empresa**: gratuito, bom para rede interna, exige PC ligado.
2. **Supabase Free**: gratuito com limites, bom para testes e pequenas operações.
3. **Neon Free**: bom para desenvolvimento e testes.
4. **Railway/Render**: podem ter limites ou mudanças de plano.
5. **VPS barato**: melhor para produção quando houver clientes pagantes.

Para começar, a opção mais simples é:

```text
PostgreSQL local em um computador/servidor da empresa
```

Para acesso externo, prefira VPN ou túnel seguro. Evite abrir PostgreSQL diretamente na internet sem entender firewall, SSL, senhas fortes e IPs permitidos.

---

## 16. Licenciamento anual

O Boxio já possui estrutura para licença em:

```text
src/licensing/license_manager.py
AppData/Boxio/Config/license.json
```

Modelo inicial:

```json
{
  "license_key": "BOXIO-2026-XXXX-XXXX",
  "company_name": "Empresa Exemplo",
  "plan": "profissional",
  "expires_at": "2027-05-13",
  "max_users": 10,
  "max_devices": 10,
  "allowed_modules": ["inventory", "purchases", "reports"]
}
```

No futuro, você pode criar uma API simples para validar licença online.

---

## 17. Checklist para publicar nova versão

1. Atualizar `APP_VERSION` em `src/core/version.py`.
2. Atualizar `DB_SCHEMA_VERSION` se mudou banco.
3. Criar migração nova se necessário.
4. Testar localmente.
5. Rodar testes manuais:
   - abrir app;
   - cadastrar item;
   - movimentar estoque;
   - exportar Excel;
   - verificar atualização;
   - conectar PostgreSQL.
6. Gerar build com PyInstaller.
7. Gerar ZIP.
8. Gerar `latest.json`.
9. Criar release no GitHub.
10. Anexar ZIP e `latest.json`.
11. Testar atualização em uma instalação antiga.

---

## 18. Compatibilidade entre versões futuras

Regra:

```text
Nunca alterar estrutura de dados sem migração versionada.
```

Exemplo:

```text
Versão 1.18.0 usa schema 16
Versão 1.18.0 usa schema 17
```

Crie:

```text
src/database/migrations/migration_017_nova_funcionalidade.py
```

Com:

```python
VERSION = 17

def up(db: dict) -> dict:
    db.setdefault("nova_tabela", [])
    return db
```

Para PostgreSQL, use scripts SQL versionados ou uma ferramenta como Alembic futuramente.

---

## 19. Próxima evolução recomendada

A ordem segura para implementar em produção é:

1. Consolidar identidade Boxio.
2. Usar PostgreSQL local em teste.
3. Migrar JSON para PostgreSQL.
4. Testar com 2 computadores.
5. Testar com 5 a 10 computadores.
6. Publicar primeira release no GitHub.
7. Testar atualização manual.
8. Implementar updater externo completo.
9. Implementar licença online.
10. Criar instalador profissional.

---

## 20. Resumo da arquitetura final

```text
Boxio Desktop em cada computador
    ↓
PostgreSQL centralizado
    ↓
GitHub Releases para atualizações
    ↓
Licença anual para controle comercial
    ↓
Logs, auditoria, permissões e backups para uso empresarial
```

Essa arquitetura mantém o sistema leve, gratuito para distribuir, preparado para múltiplos usuários e seguro para evoluir sem apagar dados dos clientes.


## Atualização v1.18.0 - Neon PostgreSQL

O projeto agora inclui `schema_neon_boxio.sql`, `init_db.py`, `.env.neon.example` e `test_neon_connection.py` para configuração direta com Neon. Use o host principal para pgAdmin/migração e o pooler apenas depois de validar o uso multiusuário.
