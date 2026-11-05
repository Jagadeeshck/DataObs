-- Certification fixture database for PostgreSQL discovery/profiling and
-- schema-boundary certification. Models a realistic multi-schema database:
--   public     — default application tables (readable by the discovery role)
--   analytics  — a second business schema the discovery role may read
--   restricted — a sensitive schema the read-only discovery role must NOT read
-- test_postgres.py asserts {public, analytics, restricted} all exist.

CREATE TABLE IF NOT EXISTS customers (id bigint PRIMARY KEY, updated_at timestamptz NOT NULL);
INSERT INTO customers VALUES (1, '2026-01-01T00:00:00Z') ON CONFLICT DO NOTHING;

-- Second readable business schema with a representative table.
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE TABLE IF NOT EXISTS analytics.order_facts (
    id bigint PRIMARY KEY,
    customer_id bigint NOT NULL,
    amount numeric(12, 2) NOT NULL,
    observed_at timestamptz NOT NULL
);
INSERT INTO analytics.order_facts VALUES (1, 1, 42.00, '2026-01-01T00:00:00Z') ON CONFLICT DO NOTHING;

-- Sensitive schema the discovery role is intentionally NOT granted access to,
-- so the fixture models a real access boundary (not just an empty namespace).
CREATE SCHEMA IF NOT EXISTS restricted;
CREATE TABLE IF NOT EXISTS restricted.pii_vault (
    id bigint PRIMARY KEY,
    customer_id bigint NOT NULL,
    secret_ref text NOT NULL
);
INSERT INTO restricted.pii_vault VALUES (1, 1, 'vault://redacted') ON CONFLICT DO NOTHING;

CREATE ROLE dataobs_readonly NOLOGIN;
GRANT CONNECT ON DATABASE orders TO dataobs_readonly;
GRANT USAGE ON SCHEMA public TO dataobs_readonly;
GRANT SELECT ON customers TO dataobs_readonly;
-- analytics is readable by the discovery role; restricted is deliberately omitted.
GRANT USAGE ON SCHEMA analytics TO dataobs_readonly;
GRANT SELECT ON analytics.order_facts TO dataobs_readonly;
