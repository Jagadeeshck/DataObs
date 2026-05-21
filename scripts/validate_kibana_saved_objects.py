#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
SO_PATH = Path('kibana/dataobs-poc-saved-objects.ndjson')
REQUIRED_DASHBOARDS=["DataObs Road Safety Executive Overview","Data Quality & Bad Data Detection","Freshness / Volume / Schema Drift","Lineage & Impact","Spark Pipeline Performance"]
REQUIRED_DATA_VIEWS={"dataobs-quality","dataobs-alerts","dataobs-freshness","dataobs-volume","dataobs-schema","dataobs-lineage","dataobs-assets","dataobs-spark-metrics","dataobs-rs-*"}
rows=[]
for i,l in enumerate(SO_PATH.read_text().splitlines(),1):
    if not l.strip():
        continue
    try: rows.append(json.loads(l))
    except Exception as e: raise SystemExit(f'Invalid NDJSON line {i}: {e}')
by_type={}
for r in rows: by_type.setdefault(r['type'],[]).append(r)
views={r['attributes']['title'] for r in by_type.get('index-pattern',[])}
miss=REQUIRED_DATA_VIEWS-views
if miss: raise SystemExit(f'Missing data views: {sorted(miss)}')
obj_by_key={(r['type'],r['id']) for r in rows}
dashes=by_type.get('dashboard',[])
for t in REQUIRED_DASHBOARDS:
    d=next((x for x in dashes if x['attributes'].get('title')==t),None)
    if not d: raise SystemExit(f'Missing dashboard: {t}')
    panels=json.loads(d['attributes'].get('panelsJSON','[]'))
    if len(panels)<5: raise SystemExit(f'Dashboard {t} has <5 panels')
    refs={r['name']:(r['type'],r['id']) for r in d.get('references',[])}
    for p in panels:
        refn=p.get('panelRefName')
        if refn not in refs: raise SystemExit(f'Dashboard {t} panel missing reference: {refn}')
        if refs[refn] not in obj_by_key: raise SystemExit(f'Dashboard {t} reference object missing: {refs[refn]}')
print(f'Validated {len(rows)} objects; dashboards are populated and references resolve.')
