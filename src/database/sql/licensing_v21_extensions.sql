-- ================================================================
-- Boxio v1.21 - Extensões recomendadas para licenciamento comercial
-- Execute no pgAdmin/Neon SQL Editor quando for criar o servidor de licenças.
-- ================================================================

CREATE SCHEMA IF NOT EXISTS boxio;
SET search_path TO boxio, public;

ALTER TABLE app_licenses
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS renewed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS notes TEXT;

ALTER TABLE device_activations
    ADD COLUMN IF NOT EXISTS token_hash TEXT,
    ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_validation_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS validation_count INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS license_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    license_id UUID REFERENCES app_licenses(id) ON DELETE SET NULL,
    activation_id UUID REFERENCES device_activations(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    event_status TEXT NOT NULL,
    message TEXT,
    device_fingerprint TEXT,
    device_name TEXT,
    app_version TEXT,
    ip_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_license_events_license_date ON license_events(license_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_license_events_company_date ON license_events(company_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_activations_license_active ON device_activations(license_id, active);
CREATE INDEX IF NOT EXISTS idx_app_licenses_key_status ON app_licenses(license_key, status);

-- Exemplo de licença anual para teste.
-- Troque company_id, chave e validade antes de usar em produção.
-- INSERT INTO app_licenses (company_id, license_key, plan, expires_at, max_users, max_devices, active, status)
-- SELECT id, 'BOXIO-TESTE-2026-0001', 'profissional', CURRENT_DATE + INTERVAL '365 days', 5, 5, TRUE, 'active'
-- FROM companies
-- WHERE name = 'Inovi'
-- LIMIT 1
-- ON CONFLICT (license_key) DO NOTHING;
