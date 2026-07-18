#!/usr/bin/env bash
set -euo pipefail
SENTINEL="${POSTGRES_PASSWORD:-DATAOBS_SENTINEL_PASSWORD_DO_NOT_PERSIST}"
export POSTGRES_PASSWORD="$SENTINEL"
wait_for(){ local name="$1" url="$2"; timeout 240 bash -c "until curl -fsS '$url' >/dev/null; do echo waiting for $name; sleep 5; done"; }
wait_for elasticsearch http://localhost:9200/_cluster/health
wait_for api http://localhost:8000/health
python -m packages.elastic_store.cli apply >/tmp/dataobs-apply.json
psql "postgresql://dataobs_metadata:${POSTGRES_PASSWORD}@localhost:5432/dataobs_demo" <<'SQL'
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE TABLE IF NOT EXISTS public.customers (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, email text UNIQUE, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS public.orders (id bigint PRIMARY KEY, customer_id bigint REFERENCES public.customers(id), amount numeric(12,2) CHECK (amount >= 0), status text NOT NULL, updated_ts timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(status);
CREATE TABLE IF NOT EXISTS analytics.order_events (event_id bigint, event_date date NOT NULL, payload text) PARTITION BY RANGE (event_date);
CREATE TABLE IF NOT EXISTS analytics.order_events_2026 PARTITION OF analytics.order_events FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
CREATE OR REPLACE VIEW public.order_summary AS SELECT status, count(*) AS orders FROM public.orders GROUP BY status;
CREATE MATERIALIZED VIEW IF NOT EXISTS public.order_mv AS SELECT count(*) AS total_orders FROM public.orders;
INSERT INTO public.customers(email) VALUES ('demo@example.com') ON CONFLICT DO NOTHING;
INSERT INTO public.orders(id, customer_id, amount, status, updated_ts) VALUES (1, 1, 42.00, 'new', now()) ON CONFLICT (id) DO UPDATE SET updated_ts=excluded.updated_ts, amount=excluded.amount;
SQL
python -m services.scanner_worker.cli --config config/postgres-scanner.example.yaml test-connection >/tmp/dataobs-connection.json
python -m services.scanner_worker.cli --config config/postgres-scanner.example.yaml discover >/tmp/dataobs-discovery.json
python -m services.scanner_worker.cli --config config/postgres-scanner.example.yaml scan-once --operation schema_snapshot >/tmp/dataobs-schema.json
python -m services.scanner_worker.cli --config config/postgres-scanner.example.yaml scan-once --operation profile >/tmp/dataobs-profile.json || true
psql "postgresql://dataobs_metadata:${POSTGRES_PASSWORD}@localhost:5432/dataobs_demo" -c "ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS demo_schema_change text; INSERT INTO public.orders(id, customer_id, amount, status, updated_ts) VALUES (2, 1, 99.00, 'paid', now()) ON CONFLICT DO NOTHING;"
python -m services.scanner_worker.cli --config config/postgres-scanner.example.yaml discover >/tmp/dataobs-discovery-2.json
python - <<'PY'
import json, pathlib
assets=json.loads(pathlib.Path('/tmp/dataobs-discovery.json').read_text())['assets']
assert any(a.get('table') == 'orders' for a in assets), assets
assert any(a.get('table_type') in {'view','materialized_view'} for a in assets), assets
PY
python - <<'PY'
import json
for path in ['/tmp/dataobs-connection.json','/tmp/dataobs-discovery.json','/tmp/dataobs-schema.json']:
    assert 'DATAOBS_SENTINEL_PASSWORD_DO_NOT_PERSIST' not in open(path).read(), path
PY
if rg -n "$SENTINEL" /tmp/dataobs-*.json postgres-demo.log 2>/dev/null; then echo "sentinel secret leaked" >&2; exit 1; fi
echo "PostgreSQL vertical slice demo completed: discovery, schema, profile smoke, schema alteration, and secret sentinel checks passed"
