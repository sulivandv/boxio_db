# Boxio — v2.2.6

**Boxio** é um sistema desktop empresarial em PySide/PyQt para controle de estoque, compras, fornecedores, movimentações, relatórios, auditoria, atualizações automáticas e preparação para licenciamento anual.

Esta versão consolida a identidade oficial **Boxio** e prepara o projeto para:

- PostgreSQL multiusuário;
- atualização gratuita via GitHub Releases;
- migração segura de JSON para SQL;
- separação entre arquivos do sistema e dados persistentes;
- operação comercial com licença anual;
- estrutura escalável para novos módulos.


## Boxio v2.2.6 — Fase 1 Render + Neon

Esta versão implementa a produção inicial do servidor de licenças com Render + Neon:

```text
Boxio Desktop
        ↓
Render Web Service executando FastAPI
        ↓
Neon PostgreSQL
```

Documentação principal:

```text
docs/PRODUCAO_RENDER_FASTAPI_NEON.md
```

Configuração esperada no desktop:

```env
BOXIO_LICENSE_SERVER_URL=https://boxio-license-server.onrender.com
BOXIO_LICENSE_OFFLINE_GRACE_DAYS=7
BOXIO_LICENSE_TIMEOUT=20
```

## Como rodar localmente

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Guia principal

Leia o guia completo para iniciantes:

```text
docs/GUIA_COMPLETO_BOXIO_INICIANTE.md
```

## Configuração PostgreSQL

Copie:

```text
config/examples/.env.example
```

Para:

```text
.env
```

Edite os dados de conexão:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=boxio
POSTGRES_USER=boxio_app
POSTGRES_PASSWORD=troque_esta_senha
POSTGRES_SSLMODE=prefer
```

Crie as tabelas:

```powershell
psql -U boxio_app -d boxio -f src/database/sql/schema_postgresql.sql
```

## Atualizações via GitHub Releases

Configure em `.env` ou em `src/core/version.py`:

```env
GITHUB_OWNER=SEU_USUARIO
GITHUB_REPO=boxio-releases
GITHUB_CHANNEL=stable
```

Publique no GitHub Releases os arquivos:

- `boxio_1.18.0.zip`
- `latest.json`

O aplicativo consulta a última release e compara com a versão instalada.

## Build Windows

```powershell
.\tools\release\create_windows_build.ps1
```

O script gera:

```text
dist/Boxio/
dist/boxio_1.18.0.zip
dist/latest.json
```

## Dados persistentes

O Boxio salva dados do cliente fora da pasta do executável:

```text
AppData/Local/Boxio/
```

Isso evita perda de dados durante atualizações.

## Boxio v1.18.0 - Integração Neon/PostgreSQL

Esta versão integra a configuração recomendada para PostgreSQL hospedado no Neon.

### Arquivos principais

```text
config/examples/.env.neon.example
src/database/sql/schema_neon_boxio.sql
src/database/postgres/init_db.py
src/database/migrations/json_to_postgres.py
test_neon_connection.py
docs/NEON_POSTGRES_BOXIO_IMPLEMENTACAO.md
```

### Passos rápidos

```bash
copy config\examples\.env.neon.example .env
pip install -r requirements.txt
python test_neon_connection.py
python -m src.database.postgres.init_db
python -m src.database.migrations.json_to_postgres --json database/inventory_db.json --company "Inovi"
```

Consulte o guia completo em `docs/NEON_POSTGRES_BOXIO_IMPLEMENTACAO.md`.

## Boxio v1.18.0 - Inventário demonstrativo e identidade Inovi

Esta versão reduz o inventário local de exemplo para **10 itens odontológicos**. Esses dados são apenas demonstrativos e foram pensados para deixar a interface mais limpa durante apresentação, testes e implantação inicial.

Empresa padrão configurada:

```text
Inovi
```

O usuário final deve cadastrar posteriormente os produtos reais da empresa/clinica.

### Observação sobre dados persistentes

Por segurança, o Boxio não sobrescreve automaticamente um banco JSON que já exista em `AppData/Local/Boxio`. Se você já executou versões anteriores e deseja carregar o novo inventário demonstrativo, substitua manualmente o arquivo persistente pelo modelo atualizado em:

```text
database/inventory_db.json
```

ou remova o banco local persistente antes da primeira abertura da nova versão.


## Boxio v1.19.1

- Camada de dados PostgreSQL/Neon integrada à interface quando `BOXIO_DB_MODE=postgresql`.
- JSON mantido apenas como fallback temporário.
- CRUD de produtos, referências, movimentações e compras preparado para banco online.
- Botão “Novo Produto” organizado como subitem do módulo Inventário.
- Novo componente visual de ajuda contextual `ℹ️`.
- Consulte `docs/POSTGRES_ONLINE_INTEGRACAO_V19.md`.


## Boxio v1.19.2 - Correções PostgreSQL/Neon e UI

Esta versão corrige o cadastro e edição de produtos com PostgreSQL/Neon, removendo o erro `AmbiguousParameter` causado por parâmetros nulos em validação de SKU.

Também foram aplicadas melhorias visuais e de usabilidade:

- formulários de Adicionar/Editar Produto com área rolável;
- melhor adaptação para telas menores;
- modais internos sem barra superior pesada, mantendo botão `X` integrado;
- ajuda contextual com janela customizada sem barra nativa;
- consultas de produtos otimizadas para reduzir lentidão no uso com banco remoto;
- cache leve para referências, unidades, categorias, marcas, fornecedores e locais;
- manutenção do PostgreSQL/Neon como fonte principal quando `BOXIO_DB_MODE=postgresql`.


## Boxio v1.19.3 - Performance UI, tabelas e ajuda contextual

Melhorias desta versão:

- Otimização da navegação entre páginas, reduzindo consultas repetidas ao PostgreSQL/Neon.
- Cache curto em memória para produtos, referências, compras, movimentações e larguras de colunas.
- Redução de chamadas remotas durante renderização de tabelas.
- Pesquisa do inventário com debounce, evitando recarregar a lista a cada tecla instantaneamente.
- Persistência de largura das colunas com atraso controlado, evitando gravações no banco a cada pixel de redimensionamento.
- Coluna Produto no inventário com largura mínima maior para leitura de nomes longos.
- Coluna Status com mais destaque visual.
- Coluna SKU com menor prioridade visual.
- Remoção do ícone de lupa dos cabeçalhos.
- Cabeçalhos agora usam indicador de filtro mais discreto e visível: ▾.
- Cabeçalhos técnicos, como Qtd. Base, passam a exibir ℹ com explicação objetiva.

Observação: a aplicação continua usando PostgreSQL/Neon como fonte principal quando `BOXIO_DB_MODE=postgresql` está configurado no `.env`.


## Boxio v1.20.0 - Performance e arquitetura cache-first

Esta versão adiciona uma camada de cache local SQLite para acelerar a interface desktop quando o banco principal está no Neon/PostgreSQL. O Neon continua sendo a fonte oficial dos dados, mas as telas passam a ler snapshots locais para abrir rapidamente. A sincronização remota é iniciada em segundo plano após a abertura do sistema.

Principais melhorias:

- Cache local persistente em `AppData/Local/Boxio/Cache/boxio_local_cache.sqlite`.
- Leitura cache-first para produtos, cadastros, movimentações e compras.
- Sincronização PostgreSQL/Neon em background, sem bloquear digitação, cliques ou troca de páginas.
- Renderização limitada/paginada na tabela de inventário: exibe rapidamente os primeiros registros e orienta o usuário a filtrar quando houver grande volume.
- Redução de chamadas remotas repetidas em dashboard, inventário e compras.
- Preparação para arquitetura offline-first/sync incremental em versões futuras.

Para forçar uma nova sincronização, cadastre/edite um item ou reinicie o sistema com o banco Neon conectado.


## Boxio v1.20.1 - Correções de compras, status e feedback visual

- Coluna Status reposicionada após SKU no inventário.
- Confirmações visuais de sucesso em ações importantes.
- Correção no recebimento de compras com PostgreSQL/Neon.
- Validação de IDs UUID antes de gravar movimentações.
- Mensagens de erro técnicas convertidas para mensagens amigáveis.
- Cache local invalidado automaticamente ao mudar a versão do aplicativo.
