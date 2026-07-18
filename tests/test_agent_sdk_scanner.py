from datetime import datetime, timezone
import time
import pytest
from packages.agent_sdk.models import *
from packages.agent_sdk.registry import ConnectorRegistry
from packages.agent_sdk.security import redact
from services.scanner_worker.worker import ScannerWorker
from services.scanner_worker.scheduler import deterministic_retry_delay
from services.scanner_worker.telemetry import otel_attributes
from integrations.databases.postgres.connector import PostgresConnector

class FakePg:
    metadata=[{'database':'db','schema':'public','table':'orders','table_type':'BASE TABLE','column':'id','type':'integer','nullable':False},{'database':'db','schema':'secret','table':'pii','table_type':'BASE TABLE','column':'ssn','type':'text','nullable':True},{'database':'db','schema':'public','table':'orders','table_type':'BASE TABLE','column':'amount','type':'numeric','nullable':True}]
    def execute(self, sql): assert 'SELECT *' not in sql; return 1
    def profile(self, opts): return {'orders.row_count':2,'orders.amount.null_rate':0.5,'orders.amount.cardinality':1}

def meta(): return ResultMetadata('tenant-a','dev','src1',ConnectorIdentity('postgres','0.1','postgres'),'exec1','task1',datetime.now(timezone.utc),None,'postgres','db.public.orders')
def test_registry_and_capabilities():
    r=ConnectorRegistry(); r.register('postgres', lambda: PostgresConnector(connection=FakePg()))
    c=r.create('postgres'); assert c.capabilities().schema_snapshot and c.capabilities().profiling and not c.capabilities().emits_raw_rows
    assert r.names()==('postgres',)
def test_task_validation_and_otel_tenant_propagation():
    task=ScanTask('t1','tenant','prod','i1','postgres','discover','postgres', options={'trace_id':'abc'}); task.validate()
    assert otel_attributes(task)['dataobs.tenant_id']=='tenant'
    with pytest.raises(ValueError): ScanTask('', 'tenant','prod','i1','postgres','discover','postgres').validate()
def test_secret_redaction_and_safe_repr():
    assert 'pw' not in redact('postgres://u:pw@host/db')
    assert redact({'password':'pw','nested':{'api_key':'k'}})['password']=='***REDACTED***'
    assert 'pw' not in repr(SecretReference('env','DB_PASSWORD'))
    assert 'pw' not in repr(PostgresConnector('postgres://u:pw@host/db'))
def test_schema_canonical_fingerprint_and_diff():
    a={'columns':[{'name':'ID','type':'INT','nullable':False}]}; b={'columns':[{'name':'id','type':'int','nullable':True},{'name':'name','type':'text'}]}
    assert schema_fingerprint(a)==schema_fingerprint({'columns':[{'nullable':False,'type':'int','name':'id'}]})
    changes=diff_schemas(a,b,'asset'); assert {c.change_type for c in changes}=={'column_added','nullable_changed'}
def test_postgres_discovery_allow_deny_snapshot_profile_checkpoint():
    c=PostgresConnector(connection=FakePg(), allow_schemas=['public'], deny_schemas=['secret'])
    assert c.test_connection().ok
    assets=c.discover(DiscoveryRequest(meta())).assets; assert all(a['schema']=='public' for a in assets)
    snap=c.schema_snapshot(SchemaScanRequest(meta())); assert snap.fingerprint and all(col['name']!='ssn' for col in snap.canonical_schema['columns'])
    off=c.profile(ProfileRequest(meta())).metrics; assert off['profiling']=='disabled'
    prof=c.profile(ProfileRequest(meta(), {'enable_aggregate_profiling':True})); assert not prof.raw_rows_persisted and prof.metrics['orders.row_count']==2
    assert 'last_profile' in c.checkpoint().cursor
def test_worker_heartbeat_timeout_and_retries():
    class Slow:
        def capabilities(self): return ConnectorCapabilities()
        def discover(self, req): time.sleep(.2)
    r=ConnectorRegistry(); r.register('slow', lambda: Slow())
    task=ScanTask('t1','tenant','prod','i1','slow','discover','postgres', timeout_seconds=1)
    worker=ScannerWorker(r); ex=worker.run(task); assert ex.error is None and ex.metadata.tenant_id=='tenant' and worker.heartbeats
    assert deterministic_retry_delay(3)==20
    class Boom(Slow):
        def discover(self, req): raise RuntimeError('boom')
    r.register('boom', lambda: Boom())
    err=ScannerWorker(r).run(ScanTask('t2','tenant','prod','i1','boom','discover','postgres'))
    assert err.error.retryable
