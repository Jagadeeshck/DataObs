from __future__ import annotations
import csv, random
from pathlib import Path
from typing import Dict, List

def _read_csv(path: Path) -> List[Dict[str,str]]:
    with path.open() as f:
        return list(csv.DictReader(f))

def generate_scaled(seed_dir: Path, out_dir: Path, scale: str = "small", large_target_rows: int = 1_000_000) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    mul = {"small": 200, "medium": 50_000}.get(scale, None)
    if scale == "large":
        mul = max(1, large_target_rows // 5)
    accidents = _read_csv(seed_dir / "accidents.csv")
    vehicles = _read_csv(seed_dir / "vehicles.csv")
    casualties = _read_csv(seed_dir / "casualties.csv")
    authorities = _read_csv(seed_dir / "local_authorities.csv")
    weather = _read_csv(seed_dir / "weather_lookup.csv")

    def write(name: str, rows: List[Dict[str,str]]):
        path = out_dir / name
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        return path

    acc_out=[]; veh_out=[]; cas_out=[]
    for i in range(mul):
        a = dict(random.choice(accidents)); a["accident_id"] = f"A{i+1}"
        if scale != "small":
            a["location_easting"] = str(int(a["location_easting"]) + random.randint(-3000, 3000))
        acc_out.append(a)
        v = dict(random.choice(vehicles)); v["vehicle_id"] = f"V{i+1}"; v["accident_id"] = a["accident_id"]; veh_out.append(v)
        c = dict(random.choice(casualties)); c["casualty_id"] = f"C{i+1}"; c["vehicle_id"] = v["vehicle_id"]; c["accident_id"] = a["accident_id"]; cas_out.append(c)
    return {
        "accidents": write("accidents.csv", acc_out),
        "vehicles": write("vehicles.csv", veh_out),
        "casualties": write("casualties.csv", cas_out),
        "local_authorities": write("local_authorities.csv", authorities),
        "weather_lookup": write("weather_lookup.csv", weather),
    }
