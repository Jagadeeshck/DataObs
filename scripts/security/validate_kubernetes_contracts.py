#!/usr/bin/env python3
"""Validate RBAC, secret/config, ingress, exception and exact-SHA evidence contracts."""
import argparse, datetime as dt, hashlib, json, re, subprocess, sys
from pathlib import Path
import yaml
RISK=re.compile(r"(password|api.?key|client.?secret|private.?key|signing.?secret|encryption.?key|authorization|credential)",re.I)
def scan(docs):
 errors=[]
 for i,d in enumerate(docs):
  if not isinstance(d,dict): continue
  kind=d.get("kind",""); name=d.get("metadata",{}).get("name",f"document-{i}")
  if kind=="ConfigMap":
   for key in d.get("data",{}):
    if RISK.search(key): errors.append({"path":name,"key":key,"rule":"secret-in-configmap","severity":"critical","fingerprint":hashlib.sha256(f"{name}:{key}".encode()).hexdigest()[:12]})
  if kind=="Ingress":
   spec=d.get("spec",{}); annotations=d.get("metadata",{}).get("annotations",{})
   if not spec.get("tls") or any(not x.get("secretName") for x in spec.get("tls",[])): errors.append({"path":name,"key":"spec.tls","rule":"ingress-tls-required","severity":"critical","fingerprint":"not-sensitive"})
   if any("configuration-snippet" in x for x in annotations): errors.append({"path":name,"key":"metadata.annotations","rule":"unsafe-ingress-snippet","severity":"high","fingerprint":"not-sensitive"})
  ps=(d.get("spec",{}).get("template",{}).get("spec",{}))
  for c in ps.get("containers",[])+ps.get("initContainers",[]):
   for env in c.get("env",[]):
    if RISK.search(env.get("name","")) and "value" in env: errors.append({"path":name,"key":env.get("name"),"rule":"secret-env-literal","severity":"critical","fingerprint":hashlib.sha256(f"{name}:{env.get('name')}".encode()).hexdigest()[:12]})
 return errors
def exceptions(path):
 now=dt.datetime.now(dt.timezone.utc); errors=[]
 for x in json.loads(Path(path).read_text()):
  if x.get("policy_id") in {None,"*"} or x.get("component") in {None,"*"}: errors.append("wildcard/missing exception scope")
  if not x.get("approval_reference") and "production" in x.get("environment_scope",[]): errors.append("production approval missing")
  try:
   expiry=dt.datetime.fromisoformat(x["expiry_time"].replace("Z","+00:00"));
   if expiry <= now: errors.append("expired exception")
  except Exception: errors.append("missing/invalid expiry")
 return errors
def evidence(path,sha):
 root=Path(path); m=json.loads((root/"manifest.json").read_text()); errors=[]
 if m.get("target_sha")!=sha: errors.append("wrong SHA")
 for name,digest in m.get("files",{}).items():
  f=root/name
  if not f.exists(): errors.append(f"missing mandatory report: {name}")
  elif hashlib.sha256(f.read_bytes()).hexdigest()!=digest: errors.append(f"checksum mismatch: {name}")
  elif name.endswith(".json"):
   data=json.loads(f.read_text())
   if data.get("overall") in {"unvalidated"} or any(x.get("state")=="UNKNOWN" and x.get("severity")=="critical" for x in data.get("policies",[])): errors.append(f"mandatory UNKNOWN: {name}")
 return errors
def main():
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="mode",required=True)
 s=sub.add_parser("manifest"); s.add_argument("path")
 e=sub.add_parser("exceptions"); e.add_argument("path")
 v=sub.add_parser("evidence"); v.add_argument("path"); v.add_argument("--sha",required=True)
 a=p.parse_args(); errors=scan(list(yaml.safe_load_all(Path(a.path).read_text()))) if a.mode=="manifest" else exceptions(a.path) if a.mode=="exceptions" else evidence(a.path,a.sha)
 print(json.dumps({"status":"FAIL" if errors else "PASS","violations":errors},indent=2)); return bool(errors)
if __name__=="__main__": sys.exit(main())
