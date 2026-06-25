# Relatório de dados demonstrativos - Boxio v1.18.0

## Objetivo

O inventário local `database/inventory_db.json` foi simplificado para uso como base demonstrativa do sistema **Boxio** na empresa **Inovi**.

## Resultado atual

- Empresa padrão: **Inovi**
- Produtos demonstrativos: **10**
- Categorias demonstrativas: **5**
- Fornecedores demonstrativos: **4**
- Marcas demonstrativas: **8**
- Movimentações iniciais demonstrativas: **10**
- Histórico fornecedor-produto demonstrativo: **10**

## Observação operacional

Os dados atuais são fictícios e servem apenas para apresentação, testes visuais e validação inicial do fluxo de inventário. O usuário final deve cadastrar posteriormente os itens reais da operação.

## Segurança de atualização

O Boxio preserva bancos já existentes no diretório persistente do usuário. Por isso, atualizar o pacote do sistema não apaga dados reais já cadastrados em `AppData/Local/Boxio`.
