# Boxio v1.20.2 — Recebimento, devolução e atualização manual

## Correções principais

- O botão **Confirmar Recebimento** agora é bloqueado imediatamente após o primeiro clique.
- A interface mostra estado de processamento enquanto a operação é executada.
- O recebimento é feito de forma transacional no PostgreSQL/Neon usando bloqueio de linha.
- IDs temporários de responsáveis ou vínculos antigos são normalizados antes de gravar colunas UUID.
- O sistema valida recebimento acima da quantidade prevista.
- Para excedente, o usuário pode escolher:
  - adicionar excedente ao estoque;
  - solicitar devolução/troca ao fornecedor;
  - cancelar para revisão.
- Foi criada estrutura `supplier_return_requests` para rastrear devolução/troca.
- Todas as páginas têm botão de atualização manual **⟳** no canto superior direito.

## Observação operacional

Execute `python -m src.database.postgres.init_db` uma vez após atualizar, para garantir a criação da tabela `supplier_return_requests` no Neon. O serviço também tenta criar essa tabela automaticamente ao iniciar.
