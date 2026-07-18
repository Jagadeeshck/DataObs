from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timedelta, timezone
import uuid
from packages.agent_sdk.models import *

class InMemoryLeaseManager:
    def acquire(self, task: ScanTask, owner: str) -> TaskLease: return TaskLease(task.task_id, owner, datetime.now(timezone.utc)+timedelta(seconds=task.timeout_seconds))
    def renew(self, lease: TaskLease) -> TaskLease: lease.version += 1; return lease
class ScannerWorker:
    def __init__(self, registry, lease_manager=None, worker_id=None): self.registry=registry; self.lease_manager=lease_manager or InMemoryLeaseManager(); self.worker_id=worker_id or 'scanner-'+uuid.uuid4().hex[:8]; self.heartbeats=[]
    def heartbeat(self, task, connector):
        hb=ScannerHeartbeat(self.worker_id, task.tenant_id, task.environment, True, connector.capabilities()); self.heartbeats.append(hb); return hb
    def run(self, task: ScanTask):
        task.validate(); connector=self.registry.create(task.connector_name); lease=self.lease_manager.acquire(task,self.worker_id); self.heartbeat(task, connector)
        md=ResultMetadata(task.tenant_id, task.environment, task.integration_id, ConnectorIdentity(task.connector_name,'0.1.0',task.source_system), 'exec-'+task.task_id, task.task_id, datetime.now(timezone.utc), None, task.source_system, task.asset_filter.get('asset','*'), correlation_trace_id=task.options.get('trace_id'))
        req=BaseRequest(md, task.options)
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut=ex.submit(getattr(connector, task.operation), req)
            try: result=fut.result(timeout=task.timeout_seconds); return ScanExecution(md, lease, result, attempts=task.attempt)
            except TimeoutError: return ScanExecution(md, lease, None, ScanError(ErrorCategory.timeout,'task timed out',True), task.attempt)
            except Exception as e: return ScanExecution(md, lease, None, ScanError(ErrorCategory.connector,str(e), task.attempt < 3), task.attempt)
