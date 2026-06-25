# Boxio v1.20.5 — Padronização total de modais e ajuda contextual

## O que foi aplicado

- Remoção de usos diretos de `QMessageBox` e `QInputDialog` em `main_window.py`.
- Substituição por modais customizados do Boxio:
  - `InfoDialog`
  - `HelpContentDialog`
  - `TextInputDialog`
  - `ActionChoiceDialog`
- Expansão da ajuda contextual para formulários e telas secundárias:
  - Produto
  - Movimentação
  - Solicitação de compra
  - Fluxo de compra
  - Recebimento
  - Comparação de fornecedores
  - Detalhes de categoria
  - Ações do item
  - Detalhamentos do dashboard
  - Cadastros administrativos
- Inclusão de ajuda nos cadastros administrativos:
  - Categorias
  - Marcas
  - Fornecedores
  - Estoques/Locais
  - Responsáveis

## Objetivo

Garantir experiência visual consistente, moderna e autoexplicativa em todo o sistema, reduzindo dúvidas operacionais e evitando pop-ups nativos desalinhados com a identidade visual do Boxio.
