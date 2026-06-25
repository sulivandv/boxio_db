CREATE SCHEMA IF NOT EXISTS boxio;
SET search_path TO boxio, public;

-- Schema PostgreSQL inicial para o Boxio empresarial.
-- Objetivo: substituir o armazenamento JSON local por banco relacional
-- centralizado, seguro e preparado para 5 a 10 usuários simultâneos.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO app_metadata (key, value)
VALUES ('schema_version', '21')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    document TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_lower_name ON companies(lower(name));

CREATE TABLE IF NOT EXISTS users_app (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    role TEXT NOT NULL DEFAULT 'operador',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, lower(name))
);

CREATE TABLE IF NOT EXISTS brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, lower(name))
);

CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    contact_name TEXT,
    phone TEXT,
    email TEXT,
    website TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, lower(name))
);

CREATE TABLE IF NOT EXISTS stock_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, lower(name))
);

CREATE TABLE IF NOT EXISTS measurement_units (
    code TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    fractionable BOOLEAN NOT NULL DEFAULT FALSE,
    decimal_precision INTEGER NOT NULL DEFAULT 0,
    base_code TEXT,
    conversion_factor NUMERIC(18,6) NOT NULL DEFAULT 1
);

INSERT INTO measurement_units (code, description, fractionable, decimal_precision, base_code, conversion_factor) VALUES
('un', 'Unidade', FALSE, 0, 'un', 1),
('cx', 'Caixa', FALSE, 0, 'cx', 1),
('pc', 'Pacote', FALSE, 0, 'pc', 1),
('ml', 'Mililitros', TRUE, 2, 'ml', 1),
('l', 'Litros', TRUE, 3, 'ml', 1000),
('g', 'Gramas', TRUE, 2, 'g', 1),
('kg', 'Quilogramas', TRUE, 3, 'g', 1000),
('lb', 'Libras', TRUE, 3, 'g', 453.59237),
('mm', 'Milímetros', TRUE, 2, 'mm', 1),
('cm', 'Centímetros', TRUE, 2, 'mm', 10),
('in', 'Polegadas', TRUE, 3, 'mm', 25.4)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    brand_id UUID REFERENCES brands(id) ON DELETE SET NULL,
    stock_location_id UUID REFERENCES stock_locations(id) ON DELETE SET NULL,
    material_type TEXT,
    unit_code TEXT REFERENCES measurement_units(code),
    quantity_base NUMERIC(18,4) NOT NULL DEFAULT 1,
    current_stock NUMERIC(18,4) NOT NULL DEFAULT 0,
    minimum_stock NUMERIC(18,4) NOT NULL DEFAULT 0,
    cost_price NUMERIC(18,2) NOT NULL DEFAULT 0,
    sale_price NUMERIC(18,2) NOT NULL DEFAULT 0,
    description TEXT,
    vendor_name TEXT,
    controls_batch BOOLEAN NOT NULL DEFAULT FALSE,
    controls_expiration BOOLEAN NOT NULL DEFAULT FALSE,
    expiration_date DATE,
    controls_serial BOOLEAN NOT NULL DEFAULT FALSE,
    abc_classification TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, sku),
    CHECK (current_stock >= 0),
    CHECK (minimum_stock >= 0),
    CHECK (quantity_base > 0)
);

CREATE INDEX IF NOT EXISTS idx_products_company_name ON products(company_id, name);
CREATE INDEX IF NOT EXISTS idx_products_company_sku ON products(company_id, sku);
CREATE INDEX IF NOT EXISTS idx_products_stock_status ON products(company_id, current_stock, minimum_stock);

CREATE TABLE IF NOT EXISTS product_supplier_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    quoted_price NUMERIC(18,2),
    paid_price NUMERIC(18,2),
    quote_date DATE,
    purchase_date DATE,
    delivery_days INTEGER,
    negotiation_status TEXT DEFAULT 'cotado',
    responsible_user_id UUID REFERENCES users_app(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_supplier_history_product ON product_supplier_history(product_id, quote_date DESC);
CREATE INDEX IF NOT EXISTS idx_supplier_history_supplier ON product_supplier_history(supplier_id, quote_date DESC);

CREATE TABLE IF NOT EXISTS stock_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    movement_type TEXT NOT NULL CHECK (movement_type IN ('entrada', 'saida', 'ajuste', 'recebimento_compra', 'cadastro_inicial')),
    quantity NUMERIC(18,4) NOT NULL,
    unit_code TEXT REFERENCES measurement_units(code),
    converted_quantity NUMERIC(18,4) NOT NULL,
    previous_stock NUMERIC(18,4) NOT NULL,
    resulting_stock NUMERIC(18,4) NOT NULL,
    responsible_user_id UUID REFERENCES users_app(id) ON DELETE SET NULL,
    source_destination TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (quantity > 0),
    CHECK (resulting_stock >= 0)
);

CREATE INDEX IF NOT EXISTS idx_movements_product_date ON stock_movements(product_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_movements_company_date ON stock_movements(company_id, created_at DESC);

CREATE TABLE IF NOT EXISTS purchase_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    requested_quantity NUMERIC(18,4) NOT NULL,
    received_quantity NUMERIC(18,4) NOT NULL DEFAULT 0,
    unit_code TEXT REFERENCES measurement_units(code),
    priority TEXT DEFAULT 'normal',
    status TEXT NOT NULL DEFAULT 'solicitacao_criada',
    justification TEXT,
    notes TEXT,
    order_number TEXT,
    order_value NUMERIC(18,2),
    expected_delivery_date DATE,
    requested_by UUID REFERENCES users_app(id) ON DELETE SET NULL,
    purchased_by UUID REFERENCES users_app(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalized_at TIMESTAMPTZ,
    CHECK (requested_quantity > 0),
    CHECK (received_quantity >= 0)
);

CREATE INDEX IF NOT EXISTS idx_purchase_status ON purchase_requests(company_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_purchase_product ON purchase_requests(product_id, status);

CREATE TABLE IF NOT EXISTS supplier_return_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    purchase_request_id UUID REFERENCES purchase_requests(id) ON DELETE SET NULL,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    quantity NUMERIC(18,4) NOT NULL CHECK (quantity > 0),
    unit_code TEXT REFERENCES measurement_units(code),
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'Pendente de devolução',
    notes TEXT,
    requested_by UUID REFERENCES users_app(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalized_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_return_requests_purchase ON supplier_return_requests(purchase_request_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_return_requests_status ON supplier_return_requests(company_id, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users_app(id) ON DELETE SET NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    action TEXT NOT NULL,
    old_data JSONB,
    new_data JSONB,
    ip_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_company_date ON audit_logs(company_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app_licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    license_key TEXT NOT NULL UNIQUE,
    plan TEXT NOT NULL DEFAULT 'profissional',
    expires_at DATE NOT NULL,
    max_users INTEGER NOT NULL DEFAULT 5,
    max_devices INTEGER NOT NULL DEFAULT 5,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    last_check_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- Permissões granulares para crescimento futuro do Boxio.
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, lower(name))
);

CREATE TABLE IF NOT EXISTS role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_key TEXT NOT NULL,
    allowed BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(role_id, permission_key)
);

ALTER TABLE users_app ADD COLUMN IF NOT EXISTS role_id UUID REFERENCES roles(id) ON DELETE SET NULL;

-- Sessões/dispositivos ajudam a controlar licença anual por computador.
CREATE TABLE IF NOT EXISTS device_activations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    license_id UUID REFERENCES app_licenses(id) ON DELETE CASCADE,
    device_fingerprint TEXT NOT NULL,
    device_name TEXT,
    last_seen_at TIMESTAMPTZ,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(license_id, device_fingerprint)
);
