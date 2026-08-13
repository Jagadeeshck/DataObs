#!/usr/bin/env python3
"""Fail-closed, engine-neutral DataObs rendered/observed Kubernetes validator."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml
from validate_kubernetes_images import check_image

WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "Pod"}


def podspec(d):
    s = d.get("spec", {})
    k = d.get("kind")
    if k == "CronJob":
        return s.get("jobTemplate", {}).get("spec", {}).get("template", {}).get("spec", {})
    if k in WORKLOADS - {"Pod"}:
        return s.get("template", {}).get("spec", {})
    return s if k == "Pod" else None


def result(pid, c, expected, observed, state, severity="critical", remediation="Apply the production security profile"):
    return {
        "policy_id": pid,
        "component": c,
        "expected": expected,
        "observed": observed,
        "state": state,
        "severity": severity,
        "evidence_source": "manifest metadata only",
        "remediation": remediation,
    }


def validate(docs, allowed):
    out = []
    network = False
    pdb = False
    for d in docs:
        if not isinstance(d, dict):
            continue
        kind = d.get("kind", "")
        name = d.get("metadata", {}).get("name", "unnamed")
        if kind == "NetworkPolicy":
            network = True
            for e in d.get("spec", {}).get("egress", []):
                for to in e.get("to", []):
                    if to.get("ipBlock", {}).get("cidr") == "0.0.0.0/0":
                        out.append(
                            result("K8S-NET-003", name, "no undocumented broad egress", "0.0.0.0/0", "FAIL", "high")
                        )
        if kind == "PodDisruptionBudget":
            pdb = True
        if kind in {"Role", "ClusterRole"}:
            for rule in d.get("rules", []):
                if any("*" in rule.get(x, []) for x in ("verbs", "resources", "apiGroups")):
                    out.append(result("K8S-RBAC-001", name, "no wildcards", "wildcard", "FAIL"))
        if kind in {"ClusterRoleBinding"}:
            out.append(result("K8S-RBAC-002", name, "namespace-scoped RBAC", "cluster binding", "FAIL"))
        ps = podspec(d)
        if ps is None:
            continue
        podsc = ps.get("securityContext", {})
        checks = [
            ("K8S-PSS-001", podsc.get("runAsNonRoot") is True, "runAsNonRoot=true", podsc.get("runAsNonRoot")),
            (
                "K8S-PSS-002",
                podsc.get("seccompProfile", {}).get("type") in {"RuntimeDefault", "Localhost"},
                "seccomp RuntimeDefault or stronger",
                podsc.get("seccompProfile"),
            ),
            (
                "K8S-HOST-001",
                not any(ps.get(x, False) for x in ("hostNetwork", "hostPID", "hostIPC")),
                "host namespaces disabled",
                {x: ps.get(x, False) for x in ("hostNetwork", "hostPID", "hostIPC")},
            ),
            (
                "K8S-SA-001",
                ps.get("automountServiceAccountToken") is False,
                "automount=false",
                ps.get("automountServiceAccountToken"),
            ),
            (
                "K8S-HOST-002",
                not any("hostPath" in v for v in ps.get("volumes", [])),
                "no hostPath",
                [v.get("name") for v in ps.get("volumes", []) if "hostPath" in v],
            ),
        ]
        for pid, ok, exp, obs in checks:
            out.append(result(pid, name, exp, obs, "PASS" if ok else "FAIL"))
        for c in ps.get("initContainers", []) + ps.get("containers", []):
            cn = f"{name}/{c.get('name','unnamed')}"
            sc = c.get("securityContext", {})
            res = c.get("resources", {})
            cchecks = [
                ("K8S-PSS-003", sc.get("privileged", False) is False, "privileged=false", sc.get("privileged", False)),
                (
                    "K8S-PSS-004",
                    sc.get("allowPrivilegeEscalation") is False,
                    "allowPrivilegeEscalation=false",
                    sc.get("allowPrivilegeEscalation"),
                ),
                (
                    "K8S-PSS-005",
                    sc.get("readOnlyRootFilesystem") is True,
                    "readOnlyRootFilesystem=true",
                    sc.get("readOnlyRootFilesystem"),
                ),
                ("K8S-PSS-006", sc.get("runAsUser", 1) != 0, "runAsUser != 0", sc.get("runAsUser", "inherited")),
                (
                    "K8S-PSS-007",
                    sc.get("capabilities", {}).get("drop") == ["ALL"]
                    or "ALL" in sc.get("capabilities", {}).get("drop", []),
                    "drop ALL",
                    sc.get("capabilities"),
                ),
                (
                    "K8S-PSS-008",
                    not sc.get("capabilities", {}).get("add"),
                    "add no capabilities",
                    sc.get("capabilities", {}).get("add", []),
                ),
                (
                    "K8S-RES-001",
                    all(res.get(k, {}).get(x) for k in ("requests", "limits") for x in ("cpu", "memory")),
                    "CPU/memory requests and limits",
                    res,
                ),
            ]
            for pid, ok, exp, obs in cchecks:
                out.append(result(pid, cn, exp, obs, "PASS" if ok else "FAIL"))
            errs = check_image(c.get("image", ""), allowed)
            out.append(
                result(
                    "K8S-IMG-001",
                    cn,
                    "immutable allowlisted digest",
                    c.get("image", "").split("@", 1)[0],
                    "PASS" if not errs else "FAIL",
                    remediation="Pin a real release digest from an approved registry",
                )
            )
    out += [
        result("K8S-NET-001", "release", "NetworkPolicy present", network, "PASS" if network else "FAIL"),
        result("K8S-PDB-001", "release", "PDB present", pdb, "PASS" if pdb else "FAIL", "high"),
    ]
    return out


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)
    r = sub.add_parser("rendered")
    r.add_argument("--manifest", required=True)
    c = sub.add_parser("cluster")
    c.add_argument("--namespace", required=True)
    c.add_argument("--release", required=True)
    c.add_argument("--context")
    c.add_argument("--acknowledge-current-context", action="store_true")
    for x in (r, c):
        x.add_argument("--allowed-registry", action="append", default=[])
        x.add_argument("--output", default="kubernetes-security-report.json")
    a = p.parse_args()
    if a.mode == "rendered":
        docs = list(yaml.safe_load_all(Path(a.manifest).read_text()))
    else:
        if not a.context and not a.acknowledge_current_context:
            p.error("cluster mode requires --context or --acknowledge-current-context")
        cmd = (
            ["kubectl"]
            + (["--context", a.context] if a.context else [])
            + [
                "-n",
                a.namespace,
                "get",
                "deploy,statefulset,daemonset,job,cronjob,networkpolicy,pdb,role,rolebinding,serviceaccount",
                "-l",
                f"app.kubernetes.io/instance={a.release}",
                "-o",
                "yaml",
            ]
        )
        data = json.loads(subprocess.run(cmd, check=True, text=True, capture_output=True).stdout)
        docs = data.get("items", [])
    results = validate(docs, a.allowed_registry)
    mandatory = [x for x in results if x["severity"] == "critical"]
    counts = {
        "mandatory_passed": sum(x["state"] == "PASS" for x in mandatory),
        "mandatory_failed": sum(x["state"] == "FAIL" for x in mandatory),
        "unknown": sum(x["state"] == "UNKNOWN" for x in mandatory),
        "advisory_failed": sum(x["state"] == "FAIL" and x["severity"] != "critical" for x in results),
    }
    overall = "compliant" if not counts["mandatory_failed"] and not counts["unknown"] else "non_compliant"
    report = {"schema_version": "1.0", "mode": a.mode, "overall": overall, "counts": counts, "policies": results}
    Path(a.output).write_text(json.dumps(report, indent=2) + "\n")
    print(overall)
    return overall != "compliant"


if __name__ == "__main__":
    sys.exit(main())
