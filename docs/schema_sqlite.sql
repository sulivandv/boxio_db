-- Modelo relacional planejado para o Boxio v10.
-- O JSON atual foi estruturado para migrar para este desenho sem perda de dados.

CREATE TABLE unidades_medida (
    id TEXT PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    tipo_material_padrao TEXT NOT NULL,
    dimensao TEXT NOT NULL,
    fracionavel INTEGER NOT NULL DEFAULT 0,
    precisao_decimal INTEGER NOT NULL DEFAULT 0,
    quantidade_base_padrao REAL NOT NULL DEFAULT 1,
    fator_para_base REAL NOT NULL DEFAULT 1,
    unidade_base TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE categorias (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    origem TEXT,
    criado_em TEXT,
    atualizado_em TEXT
);

CREATE TABLE marcas (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    origem TEXT,
    criado_em TEXT,
    atualizado_em TEXT
);

CREATE TABLE fornecedores (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    origem TEXT,
    criado_em TEXT,
    atualizado_em TEXT
);

CREATE TABLE estoques (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    origem TEXT,
    criado_em TEXT,
    atualizado_em TEXT
);

CREATE TABLE responsaveis (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    origem TEXT,
    criado_em TEXT,
    atualizado_em TEXT
);

CREATE TABLE produtos (
    id TEXT PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    sku_legado TEXT,
    nome TEXT NOT NULL,
    categoria_id TEXT NOT NULL REFERENCES categorias(id),
    marca_id TEXT REFERENCES marcas(id),
    fornecedor_id TEXT REFERENCES fornecedores(id),
    estoque_id TEXT REFERENCES estoques(id),
    tipo_material TEXT,
    unidade_medida TEXT NOT NULL REFERENCES unidades_medida(codigo),
    quantidade_base REAL NOT NULL DEFAULT 1,
    estoque_atual REAL NOT NULL DEFAULT 0,
    estoque_minimo REAL NOT NULL DEFAULT 0,
    preco_custo REAL NOT NULL DEFAULT 0,
    preco_venda REAL NOT NULL DEFAULT 0,
    descricao TEXT,
    controla_lote INTEGER NOT NULL DEFAULT 0,
    controla_validade INTEGER NOT NULL DEFAULT 0,
    data_validade TEXT,
    controla_serial INTEGER NOT NULL DEFAULT 0,
    compra_status TEXT,
    ultima_solicitacao_compra_id TEXT,
    metadados_json TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT,
    atualizado_em TEXT
);

CREATE INDEX idx_produtos_sku ON produtos(sku);
CREATE INDEX idx_produtos_categoria ON produtos(categoria_id);
CREATE INDEX idx_produtos_status_estoque ON produtos(estoque_atual, estoque_minimo);

CREATE TABLE movimentacoes (
    id TEXT PRIMARY KEY,
    produto_id TEXT NOT NULL REFERENCES produtos(id),
    tipo TEXT NOT NULL,
    quantidade REAL NOT NULL,
    unidade_utilizada TEXT NOT NULL,
    quantidade_convertida REAL NOT NULL,
    unidade_estoque TEXT NOT NULL,
    quantidade_fisica REAL,
    saldo_anterior REAL NOT NULL,
    saldo_restante REAL NOT NULL,
    responsavel_id TEXT REFERENCES responsaveis(id),
    origem_destino TEXT,
    observacao TEXT,
    purchase_request_id TEXT,
    criado_em TEXT NOT NULL
);

CREATE TABLE solicitacoes_compra (
    id TEXT PRIMARY KEY,
    produto_id TEXT NOT NULL REFERENCES produtos(id),
    status TEXT NOT NULL,
    quantidade_solicitada REAL NOT NULL,
    quantidade_recebida REAL NOT NULL DEFAULT 0,
    unidade_medida TEXT NOT NULL,
    solicitante_id TEXT REFERENCES responsaveis(id),
    responsavel_compra_id TEXT REFERENCES responsaveis(id),
    fornecedor_id TEXT REFERENCES fornecedores(id),
    numero_pedido TEXT,
    valor REAL,
    previsao_entrega TEXT,
    prioridade TEXT,
    justificativa TEXT,
    observacao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT,
    atualizado_em TEXT
);

CREATE TABLE atividades (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    descricao TEXT,
    produto_id TEXT REFERENCES produtos(id),
    quantidade REAL,
    unidade TEXT,
    responsavel_id TEXT REFERENCES responsaveis(id),
    link_id TEXT,
    status TEXT,
    criado_em TEXT
);

CREATE TABLE auditoria (
    id TEXT PRIMARY KEY,
    entidade TEXT NOT NULL,
    entidade_id TEXT NOT NULL,
    acao TEXT NOT NULL,
    antes_json TEXT,
    depois_json TEXT,
    usuario TEXT,
    criado_em TEXT NOT NULL
);


-- Versão 11: histórico comercial por fornecedor e item
CREATE TABLE IF NOT EXISTS supplier_item_history (
    id TEXT PRIMARY KEY,
    produto_id TEXT NOT NULL,
    fornecedor_id TEXT NOT NULL,
    codigo_fornecedor TEXT,
    preco_cotado NUMERIC DEFAULT 0,
    preco_pago NUMERIC DEFAULT 0,
    melhor_preco_registrado NUMERIC DEFAULT 0,
    variacao_percentual NUMERIC DEFAULT 0,
    data_cotacao TEXT,
    data_compra TEXT,
    prazo_entrega_dias INTEGER DEFAULT 0,
    status_negociacao TEXT,
    responsavel_id TEXT,
    observacao TEXT,
    origem TEXT,
    ativo INTEGER DEFAULT 1,
    criado_em TEXT,
    atualizado_em TEXT,
    FOREIGN KEY (produto_id) REFERENCES products(id),
    FOREIGN KEY (fornecedor_id) REFERENCES suppliers(id),
    FOREIGN KEY (responsavel_id) REFERENCES responsibles(id)
);

CREATE INDEX IF NOT EXISTS idx_supplier_item_history_produto ON supplier_item_history(produto_id);
CREATE INDEX IF NOT EXISTS idx_supplier_item_history_fornecedor ON supplier_item_history(fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_supplier_item_history_datas ON supplier_item_history(data_cotacao, data_compra);

-- =============================================================
-- v14 - Estrutura para atualização contínua, licenciamento e versões
-- =============================================================
CREATE TABLE IF NOT EXISTS app_versions (
    id TEXT PRIMARY KEY,
    app_version TEXT NOT NULL,
    db_schema_version INTEGER NOT NULL,
    channel TEXT NOT NULL DEFAULT 'stable',
    installed_at TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS update_history (
    id TEXT PRIMARY KEY,
    from_version TEXT,
    to_version TEXT NOT NULL,
    package_sha256 TEXT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    rollback_backup_path TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS licenses (
    id TEXT PRIMARY KEY,
    license_key TEXT NOT NULL UNIQUE,
    customer_id TEXT,
    company_name TEXT,
    plan TEXT,
    expires_at TEXT,
    max_users INTEGER,
    max_devices INTEGER,
    latest_allowed_version TEXT,
    last_online_check TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
);
