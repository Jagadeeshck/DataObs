CREATE TABLE IF NOT EXISTS customers (id bigint PRIMARY KEY, updated_at timestamptz NOT NULL);
INSERT INTO customers VALUES (1, '2026-01-01T00:00:00Z') ON CONFLICT DO NOTHING;
CREATE ROLE dataobs_readonly NOLOGIN;
GRANT CONNECT ON DATABASE orders TO dataobs_readonly;
GRANT USAGE ON SCHEMA public TO dataobs_readonly;
GRANT SELECT ON customers TO dataobs_readonly;
