# Boxio v1.20.1 — Correções de UI, feedback e compras

## Correções aplicadas

- A coluna **Status** do inventário foi reposicionada imediatamente após **SKU**.
- A coluna **Produto** recebeu largura mínima maior para melhorar a leitura.
- O cabeçalho da tabela continua com filtro inteligente, mas sem ícone de lupa.
- Foram adicionadas confirmações visuais em formato de toast para ações importantes:
  - cadastro de produto;
  - edição de produto;
  - movimentação de estoque;
  - solicitação de compra;
  - exclusão/desativação;
  - confirmação de recebimento.
- O fluxo de recebimento de compras passou a buscar a solicitação diretamente no Neon/PostgreSQL, ignorando cache local antigo.
- Foi adicionada validação de UUID para impedir que IDs temporários/legados sejam enviados para colunas UUID do PostgreSQL.
- Erros técnicos de banco agora são convertidos para mensagens mais amigáveis ao usuário.
- O cache local SQLite é limpo automaticamente quando a versão do app muda, evitando snapshots incompatíveis de versões anteriores.

## Causa provável do erro no recebimento de compra

O erro exibido na imagem indicava que a aplicação tentou inserir na tabela `stock_movements` um `product_id` inválido, com formato temporário/legado. Isso podia ocorrer quando o fluxo de compras usava um snapshot antigo do cache local em vez de consultar a solicitação atual diretamente no banco online.

A correção garante que operações críticas, como recebimento de compra, busquem a solicitação diretamente no PostgreSQL/Neon antes de atualizar estoque.
