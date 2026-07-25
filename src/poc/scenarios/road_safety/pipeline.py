from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.poc.spark_metrics import metric_doc

SEVERITY = {"1": "Fatal", "2": "Serious", "3": "Slight"}


def _read(path: Path):
    with path.open() as f:
        return list(csv.DictReader(f))


def run_road_safety_scenario(data_dir: Path, run_id: str, run_mode: str = "good") -> Dict[str, Any]:
    accidents = _read(data_dir / "accidents.csv")
    vehicles = _read(data_dir / "vehicles.csv")
    casualties = _read(data_dir / "casualties.csv")
    la = {r["local_authority_code"]: r for r in _read(data_dir / "local_authorities.csv")}
    w = {r["weather_code"]: r for r in _read(data_dir / "weather_lookup.csv")}
    if run_mode == "bad":
        accidents = accidents[: max(1, int(len(accidents) * 0.5))]
        if accidents:
            accidents.append(dict(accidents[0]))
        for a in accidents[: max(1, len(accidents) // 2)]:
            a["local_authority_code"] = ""
        if accidents:
            accidents[0]["severity_code"] = "9"
            accidents[0]["ingested_at"] = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        if casualties:
            casualties[0]["casualty_age"] = "-5"
            casualties[0]["accident_id"] = "ORPHAN"
    a_map = {a["accident_id"]: a for a in accidents}
    v_map = {v["vehicle_id"]: v for v in vehicles}
    facts = []
    for c in casualties:
        a = a_map.get(c["accident_id"])
        v = v_map.get(c.get("vehicle_id", ""))
        if not a or not v:
            continue
        dt = datetime.fromisoformat(a["accident_date"])
        age = int(c["casualty_age"]) if c["casualty_age"].lstrip("-").isdigit() else -1
        facts.append(
            {
                "@timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "run_mode": run_mode,
                "scenario": "road_safety",
                "accident_id": a["accident_id"],
                "accident_month": dt.month,
                "accident_year": dt.year,
                "severity_label": SEVERITY.get(a["severity_code"], "Unknown"),
                "casualty_age_band": "0-17" if age < 18 else "18-64" if age < 65 else "65+",
                "road_risk_category": "HIGH" if a["road_type"] in {"Roundabout", "One way street"} else "MEDIUM",
                "weather_risk_category": w.get(a["weather_code"], {}).get("weather_risk_category", "UNKNOWN"),
                "local_authority_name": la.get(a.get("local_authority_code", ""), {}).get(
                    "local_authority_name", "Unknown"
                ),
                "vehicle_type": v.get("vehicle_type", "Unknown"),
            }
        )
    sev = Counter(f["severity_label"] for f in facts)
    checks = []

    def add(name, status, details):
        checks.append(
            {
                "@timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "run_mode": run_mode,
                "scenario": "road_safety",
                "check_name": name,
                "status": status,
                "details": details,
                }
        )

    add("duplicate_accident_ids", "fail" if len({a["accident_id"] for a in accidents}) < len(accidents) else "pass", {})
    add("invalid_severity_codes", "fail" if any(a["severity_code"] not in SEVERITY for a in accidents) else "pass", {})
    add(
        "invalid_age_values",
        (
            "fail"
            if any(
                (not c["casualty_age"].lstrip("-").isdigit())
                or int(c["casualty_age"]) < 0
                or int(c["casualty_age"]) > 110
                for c in casualties
            )
            else "pass"
        ),
        {},
    )
    add("referential_integrity", "fail" if any(c["accident_id"] not in a_map for c in casualties) else "pass", {})
    add(
        "freshness_sla",
        (
            "fail"
            if any(
                datetime.fromisoformat(a["ingested_at"]).replace(tzinfo=timezone.utc)
                < datetime.now(timezone.utc) - timedelta(hours=24)
                for a in accidents
                if a.get("ingested_at")
            )
            else "pass"
        ),
        {},
    )
    add("volume_threshold", "fail" if run_mode == "bad" else "pass", {"rows": len(accidents)})
    add("severity_distribution_drift", "fail" if sev.get("Fatal", 0) > max(1, len(facts) * 0.4) else "pass", dict(sev))
    outputs = {
        "dataobs-rs-accident-facts": facts,
        "dataobs-rs-authority-risk-summary": [
            {
                "@timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "run_mode": run_mode,
                "scenario": "road_safety",
                "local_authority_name": k,
                "incident_count": v,
            }
            for k, v in Counter(f["local_authority_name"] for f in facts).items()
        ],
        "dataobs-rs-road-risk-summary": [
            {
                "@timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "run_mode": run_mode,
                "scenario": "road_safety",
                "road_risk_category": k,
                "incident_count": v,
            }
            for k, v in Counter(f["road_risk_category"] for f in facts).items()
        ],
        "dataobs-rs-vehicle-risk-summary": [
            {
                "@timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "run_mode": run_mode,
                "scenario": "road_safety",
                "vehicle_type": k,
                "incident_count": v,
            }
            for k, v in Counter(f["vehicle_type"] for f in facts).items()
        ],
        "dataobs-rs-casualty-severity-summary": [
            {
                "@timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "run_mode": run_mode,
                "scenario": "road_safety",
                "severity_label": k,
                "incident_count": v,
            }
            for k, v in sev.items()
        ],
    }
    spark = [metric_doc(run_id, "road_safety_transform", len(casualties), len(facts), "success", 0)]
    return {"outputs": outputs, "quality": checks, "spark_metrics": spark}
