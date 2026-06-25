# Boxio v2.2.2 — Correção do .env e remoção do Filtro Inteligente da Coluna

## Correções aplicadas

### 1. Leitura do `.env`

Foi confirmado que a mensagem:

```text
Servidor de licenças não configurado. Defina BOXIO_LICENSE_SERVER_URL no .env.
```

ocorria porque o Boxio Desktop importava módulos de licenciamento antes de carregar o `.env` da raiz do projeto.

Correções:

- `main.py` agora executa `load_dotenv(ROOT_DIR / ".env", override=True)` antes dos imports do licenciamento;
- `src/licensing/license_client.py` agora lê `BOXIO_LICENSE_SERVER_URL` no momento de criação do cliente HTTP, não no import do módulo.

### 2. Remoção do Filtro Inteligente da Coluna

A funcionalidade responsável por abrir a janela "Filtro Inteligente da Coluna" foi removida.

Alterações:

- removido `AdvancedFilterDialog`;
- removido `HeaderFilterEvent`;
- removido o ícone/indicador `▾` dos cabeçalhos;
- removido o evento de clique no canto direito do cabeçalho;
- mantida a ordenação padrão ao clicar no cabeçalho;
- mantida a busca/filtro principal das telas;
- `apply_table_filters()` foi preservada como função de compatibilidade sem abrir janelas.

## Configuração esperada no `.env` da raiz do Boxio

```env
BOXIO_LICENSE_SERVER_URL=http://127.0.0.1:8000
BOXIO_LICENSE_OFFLINE_GRACE_DAYS=7
BOXIO_LICENSE_TIMEOUT=12
```

## Versão

Boxio v2.2.2
