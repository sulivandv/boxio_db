-- Boxio License Server - schema PostgreSQL/Neon
-- O servidor também cria as tabelas automaticamente ao iniciar.
-- Este arquivo existe para consulta e execução manual se preferir.

CREATE SCHEMA IF NOT EXISTS licensing;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
