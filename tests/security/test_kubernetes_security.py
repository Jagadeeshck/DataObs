import json, sys
from pathlib import Path
import yaml
sys.path.insert(0,str(Path(__file__).parents[2]/"scripts/security"))
from validate_kubernetes_images import check_image
from validate_kubernetes_runtime import validate
from validate_kubernetes_contracts import scan, exceptions, evidence
GOOD="ghcr.io/acme/api@sha256:"+"0123456789abcdef"*4
def workload(**changes):
 pod={"automountServiceAccountToken":False,"securityContext":{"runAsNonRoot":True,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"api","image":GOOD,"securityContext":{"allowPrivilegeEscalation":False,"readOnlyRootFilesystem":True,"capabilities":{"drop":["ALL"]}},"resources":{"requests":{"cpu":"1m","memory":"1Mi"},"limits":{"cpu":"1m","memory":"1Mi"}}}]}
 pod.update(changes); return {"apiVersion":"apps/v1","kind":"Deployment","metadata":{"name":"api"},"spec":{"template":{"spec":pod}}}
def failures(doc): return {x["policy_id"] for x in validate([doc,{"kind":"NetworkPolicy","metadata":{"name":"n"},"spec":{}},{"kind":"PodDisruptionBudget","metadata":{"name":"p"}}],[r"ghcr[.]io"]) if x["state"]=="FAIL"}
def test_valid_digest(): assert not check_image(GOOD,[r"ghcr[.]io"])
def test_bad_images():
 for image in ["ghcr.io/a:x","ghcr.io/a:latest","ghcr.io/a@bad","ghcr.io/a@sha256:"+"1"*64]: assert check_image(image,[r"ghcr[.]io"])
def test_security_context_and_host_rejections():
 mutations=[("K8S-PSS-001",{"securityContext":{"runAsNonRoot":False,"seccompProfile":{"type":"RuntimeDefault"}}}), ("K8S-PSS-002",{"securityContext":{"runAsNonRoot":True}}),("K8S-HOST-001",{"hostNetwork":True}),("K8S-HOST-001",{"hostPID":True}),("K8S-HOST-001",{"hostIPC":True}),("K8S-HOST-002",{"volumes":[{"hostPath":{"path":"/"}}]}),("K8S-SA-001",{"automountServiceAccountToken":True})]
 for policy,change in mutations: assert policy in failures(workload(**change))
 cchanges=[("K8S-PSS-003",{"privileged":True}),("K8S-PSS-004",{"allowPrivilegeEscalation":True}),("K8S-PSS-005",{"readOnlyRootFilesystem":False}),("K8S-PSS-006",{"runAsUser":0}),("K8S-PSS-008",{"capabilities":{"drop":["ALL"],"add":["SYS_ADMIN"]}}),("K8S-RES-001",{"resources":{}})]
 for policy,change in cchanges:
  d=workload(); c=d["spec"]["template"]["spec"]["containers"][0]
  if "resources" in change: c.update(change)
  else: c["securityContext"].update(change)
  assert policy in failures(d)
def test_rbac_network():
 role={"kind":"Role","metadata":{"name":"bad"},"rules":[{"verbs":["*"],"resources":["pods"],"apiGroups":[""]}]}; binding={"kind":"ClusterRoleBinding","metadata":{"name":"bad"}}
 out=validate([role,binding],[]); assert {"K8S-RBAC-001","K8S-RBAC-002","K8S-NET-001"} <= {x["policy_id"] for x in out if x["state"]=="FAIL"}
 broad={"kind":"NetworkPolicy","metadata":{"name":"bad"},"spec":{"egress":[{"to":[{"ipBlock":{"cidr":"0.0.0.0/0"}}]}]}}; assert "K8S-NET-003" in {x["policy_id"] for x in validate([broad],[]) if x["state"]=="FAIL"}
def test_secret_rules():
 assert scan([{"kind":"ConfigMap","metadata":{"name":"x"},"data":{"client_secret":"redacted"}}])
 assert scan([{"kind":"Deployment","metadata":{"name":"x"},"spec":{"template":{"spec":{"containers":[{"env":[{"name":"PASSWORD","value":"redacted"}]}]}}}}])
 assert not scan([{"kind":"Deployment","metadata":{"name":"x"},"spec":{"template":{"spec":{"containers":[{"env":[{"name":"PASSWORD","valueFrom":{"secretKeyRef":{"name":"x","key":"p"}}}]}]}}}}])
def test_exceptions(tmp_path):
 p=tmp_path/"e.json"; p.write_text(json.dumps([{"policy_id":"*","component":"*","environment_scope":["production"],"expiry_time":"2020-01-01T00:00:00Z"}]))
 e=exceptions(p); assert "wildcard/missing exception scope" in e and "production approval missing" in e and "expired exception" in e
def test_evidence_fail_closed(tmp_path):
 f=tmp_path/"report.json"; f.write_text(json.dumps({"policies":[{"state":"UNKNOWN","severity":"critical"}]})); import hashlib
 (tmp_path/"manifest.json").write_text(json.dumps({"target_sha":"wrong","files":{"report.json":hashlib.sha256(f.read_bytes()).hexdigest(),"missing.json":"x"}}))
 e=evidence(tmp_path,"right"); assert "wrong SHA" in e and any("missing mandatory" in x for x in e) and any("mandatory UNKNOWN" in x for x in e)
 f.write_text("tamper"); assert any("checksum mismatch" in x for x in evidence(tmp_path,"wrong"))
