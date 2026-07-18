#!/usr/bin/env python3
"""Create deterministic, tenant-isolated Console summary and topology fixtures."""
from datetime import datetime, timezone
from packages.elastic_store.client import make_client

def main():
    es=make_client(); now=datetime.now(timezone.utc).isoformat()
    for tenant,environment in (("acme-retail","production"),("northstar","staging")):
        es.index(index="dataobs-command-center-summary-v1-write",id=f"{tenant}:{environment}",document={"@timestamp":now,"tenant_id":tenant,"environment":environment,"overall_health":"critical" if tenant=="acme-retail" else "healthy","pillars":[],"priority_items":[],"recent_changes":[],"data_status":{"complete":False,"warnings":["Demo has partial pillar coverage"],"sources":["demo"],"observed_at":now}})
        for number,kind in enumerate(("source","service","topic","job","dataset")):
            es.index(index="dataobs-pathway-nodes-v1-write",id=f"{tenant}-{number}",document={"id":f"{tenant}-{number}","tenant_id":tenant,"environment":environment,"name":f"{kind}-{number}","type":kind,"health":"critical" if number==2 else "healthy","@timestamp":now})
    es.indices.refresh(index="dataobs-*"); print("Seeded isolated Console fixtures for two tenants")
if __name__=="__main__": main()
