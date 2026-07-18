from __future__ import annotations
from datetime import datetime, timezone
from packages.agent_sdk.models import *
from packages.agent_sdk.security import redact

class PostgresConnector:
    def __init__(self, dsn=None, connection=None, allow_schemas=None, deny_schemas=None, statement_timeout_ms=5000, application_name='dataobs_scanner'):
        self.dsn=dsn; self.connection=connection; self.allow=set(allow_schemas or []); self.deny=set(deny_schemas or []); self.timeout=statement_timeout_ms; self.application_name=application_name; self._checkpoint={}
    def __repr__(self): return f"PostgresConnector(dsn={redact(self.dsn or '')!r}, statement_timeout_ms={self.timeout})"
    def capabilities(self): return ConnectorCapabilities(freshness=True, profiling=True, quality=True)
    def test_connection(self):
        try:
            if self.connection and hasattr(self.connection,'execute'): self.connection.execute('SELECT 1')
            return ConnectionTestResult(True)
        except Exception as e: return ConnectionTestResult(False, str(redact(str(e))), ErrorCategory.network)
    def _filter_schema(self, schema): return (not self.allow or schema in self.allow) and schema not in self.deny
    def _metadata(self):
        if self.connection and hasattr(self.connection,'metadata'): return self.connection.metadata
        return []
    def discover(self, request):
        assets=[]
        for row in self._metadata():
            if self._filter_schema(row['schema']): assets.append({k:row[k] for k in ('database','schema','table','table_type') if k in row})
        request.metadata.ended_at=datetime.now(timezone.utc); return DiscoveryResult(request.metadata, assets)
    def schema_snapshot(self, request):
        cols=[]
        for r in self._metadata():
            if self._filter_schema(r['schema']):
                cols.append({'name':r['column'],'type':self._norm_type(r['type']),'native_type':r['type'],'nullable':bool(r.get('nullable',True)),'default':r.get('default')})
        canonical=canonicalize_schema({'columns':cols}); fp=schema_fingerprint(canonical); request.metadata.ended_at=datetime.now(timezone.utc); return SchemaSnapshot(request.metadata, canonical, fp)
    def profile(self, request):
        if not request.options.get('enable_aggregate_profiling', False):
            return ProfileResult(request.metadata, {'profiling':'disabled'}, raw_rows_persisted=False)
        metrics={}
        if self.connection and hasattr(self.connection,'profile'): metrics=self.connection.profile(request.options)
        request.metadata.ended_at=datetime.now(timezone.utc); self._checkpoint['last_profile']=request.metadata.ended_at.isoformat(); return ProfileResult(request.metadata, metrics, raw_rows_persisted=False)
    def freshness(self, request): return FreshnessResult(request.metadata, {})
    def quality(self, request): return QualityResult(request.metadata, [])
    def lineage(self, request): return LineageResult(request.metadata, [])
    def query_history(self, request): return QueryHistoryResult(request.metadata, [])
    def checkpoint(self): return ConnectorCheckpoint('postgres', 'unknown', 'unknown', self._checkpoint)
    def close(self): pass
    @staticmethod
    def _norm_type(t):
        t=t.lower()
        if 'int' in t: return 'integer'
        if any(x in t for x in ['char','text']): return 'string'
        if any(x in t for x in ['timestamp','date','time']): return 'timestamp'
        if any(x in t for x in ['numeric','decimal','double','real']): return 'number'
        return t
