#!/usr/bin/env bash
set -euo pipefail
SENTINEL="DATAOBS_SENTINEL_SECRET_DO_NOT_LEAK"
echo "Applying incident automation demo flow without printing sentinel credentials"
./bin/dataobs elastic plan >/tmp/dataobs-elastic-plan.json
./bin/dataobs workflows validate >/tmp/dataobs-workflows-validate.json
python - <<'PY'
from services.incident_manager import IncidentManagerService
svc=IncidentManagerService()
r1=svc.ingest({'id':'schema-1','event_type':'schema_change','tenant_id':'demo','environment':'prod','asset_id':'postgres.public.orders','severity':'critical','summary':'Dropped column affects downstream consumers','downstream_impact':['mart.orders']}, tenant_id='demo')
r2=svc.ingest({'id':'schema-1','event_type':'schema_change','tenant_id':'demo','environment':'prod','asset_id':'postgres.public.orders','severity':'critical','summary':'Duplicate signal','downstream_impact':['mart.orders']}, tenant_id='demo')
assert r1['incident']['id'] == r2['incident']['id']
print('incident_id='+r1['incident']['id'])
PY
