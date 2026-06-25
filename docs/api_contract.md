# Contrato REST futuro - Boxio v10

Base planejada: `/api/v1`.

## Produtos

- `GET /produtos`
- `GET /produtos/{id}`
- `POST /produtos`
- `PUT /produtos/{id}`
- `DELETE /produtos/{id}`

Campos principais: `id`, `sku`, `nome`, `categoria_id`, `marca_id`, `fornecedor_id`, `unidade_medida`, `quantidade_base`, `estoque_atual`, `estoque_minimo`, `preco_custo`, `controla_validade`, `data_validade`, `metadados`.

## Cadastros auxiliares

- `GET/POST/PUT/DELETE /categorias`
- `GET/POST/PUT/DELETE /marcas`
- `GET/POST/PUT/DELETE /fornecedores`
- `GET/POST/PUT/DELETE /estoques`
- `GET/POST/PUT/DELETE /responsaveis`

Todos devem validar nomes únicos e impedir exclusão quando existirem vínculos ativos.

## Movimentações

- `GET /movimentacoes`
- `POST /movimentacoes`

A API deve validar unidade inteira/fracionária, converter unidades compatíveis e gravar saldo anterior/restante.

## Compras

- `GET /compras`
- `POST /compras/solicitacoes`
- `PUT /compras/{id}/status`
- `POST /compras/{id}/recebimentos`

Status previstos: `Solicitação Criada`, `Em Análise`, `Aguardando Aprovação`, `Aguardando Pedido`, `Pedido Realizado`, `Compra Parcial Recebida`, `Compra Recebida Integralmente`, `Finalizado`, `Cancelado`, `Rejeitado`.

## Dashboard

- `GET /dashboard`
- `GET /dashboard/estoque-baixo`

A resposta de `estoque-baixo` deve retornar a coluna lógica `status` com os valores: `Sem estoque`, `Estoque baixo` ou `Em estoque`.


## Versão 11 - Endpoints conceituais para fornecedores e histórico comercial

### GET /products/{product_id}/supplier-history
Retorna o histórico de cotações, compras e preços pagos vinculados a um item.

### POST /products/{product_id}/supplier-history
Cria um novo registro comercial sem sobrescrever registros anteriores. Campos esperados: `fornecedor_id`, `preco_cotado`, `preco_pago`, `data_cotacao`, `data_compra`, `prazo_entrega_dias`, `status_negociacao`, `responsavel_id` e `observacao`.

### GET /products/{product_id}/supplier-comparison
Retorna indicadores calculados: menor preço, melhor prazo, fornecedor mais utilizado e histórico ordenado.

### GET /products/sku-preview
Recebe `categoria_id`, `nome`, `marca_id` e `tipo_material`, retornando a próxima prévia de SKU no padrão interno.

## v12 — Serviço de exportação local para Excel

A exportação é implementada na camada de interface como uma função reutilizável:

- `export_table_to_excel(parent, table, default_name)`
- Entrada: uma `QTableWidget` já renderizada.
- Regra: exporta linhas selecionadas; caso não haja seleção, exporta linhas visíveis após filtros.
- Saída: arquivo `.xlsx` salvo no caminho escolhido pelo usuário.
- Campos ocultos, como IDs técnicos, não são exportados.

Essa abordagem mantém compatibilidade com futuras APIs, pois a exportação opera sobre a visão atual da tabela. Em versões futuras, pode ser substituída por um serviço backend que exporte diretamente a partir de consultas SQLite/PostgreSQL.

## v14 — Endpoint de Atualização

### GET `/latest.json`

Retorna o manifesto público da versão mais recente disponível para o canal contratado.

```json
{
  "product": "boxio",
  "channel": "stable",
  "latest_version": "1.14.0",
  "minimum_supported_version": "1.10.0",
  "db_schema_version": 14,
  "mandatory": false,
  "release_date": "2026-05-13",
  "download_url": "https://.../boxio_v1.14.0.zip",
  "installer_url": "https://.../boxio_setup_v1.14.0.exe",
  "sha256": "hash_do_pacote",
  "signature": "assinatura_futura",
  "notes": ["Melhoria 1", "Correção 2"]
}
```

### Validações obrigatórias no cliente

- `product` deve corresponder ao produto instalado;
- `channel` deve corresponder ao canal local;
- `latest_version` deve ser maior que a versão instalada;
- `sha256` deve bater com o arquivo baixado;
- antes da aplicação da atualização, deve ser criado backup local.

## Futuro endpoint de licença anual

### POST `/license/validate`

Payload sugerido:

```json
{
  "license_key": "CEST-2026-XXXX",
  "app_version": "1.14.0",
  "device_id": "hash_do_dispositivo"
}
```

Resposta sugerida:

```json
{
  "active": true,
  "plan": "profissional",
  "expires_at": "2027-05-13",
  "latest_allowed_version": "1.20.0",
  "allowed_modules": ["inventory", "purchases", "reports", "supplier_history"]
}
```
