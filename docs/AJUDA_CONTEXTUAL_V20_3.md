# Boxio v1.20.3 — Ajuda contextual dos formulários

## O que foi adicionado

- Ícones de ajuda **i** padronizados ao lado de títulos e campos principais dos formulários.
- Janela explicativa detalhada ao clicar no ícone.
- Conteúdo com:
  - descrição do campo;
  - quando utilizar;
  - como preencher;
  - exemplos práticos;
  - impacto no sistema.

## Formulários priorizados nesta versão

- Cadastro/Edição de Produto
- Movimentação de Estoque
- Solicitação de Compra
- Fluxo de Compra / Recebimento
- Seção Atividade recente

## Observação técnica

O catálogo de ajudas foi centralizado em `src/ui/main_window.py` na estrutura `HELP_CONTENTS`, facilitando manutenção futura e expansão para novos módulos.
