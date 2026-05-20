""" 
src/poc/etl.py
──────────────
Dataset ETL: download → parse → normalise → bulk-ingest to Elasticsearch.

Three real public datasets are handled (road-safety CSV, air-quality CSV,
local-authority CSV).  A fourth generic fallback handles any CSV/JSON/XLSX
resource discovered by datasets.py.

For each dataset the ETL:
  1. Downloads the file (streaming, with progress log every 10 MB).
  2. Detects encoding (chardet) and parses into a list of dicts.
  3. Infers an Elasticsearch mapping via _infer_mapping() — no pre-defined
     schema required.  Date-looking strings → date, int-looking → long,
     float-looking → double, everything else → keyword.
  4. Ensures the target index exists with the inferred mapping.
  5. Bulk-indexes all rows, adding @timestamp / dataset / run_id / theme
     envelope fields so every Kibana dashboard has a consistent time axis.

Indexes created:
  dataobs-raw-road-safety           — road accident / casualty records
  dataobs-raw-air-quality           — AURN monitoring site records
  dataobs-raw-local-authority       — LA district name/code records
  dataobs-raw-<name>                — generic fallback for other sources

A summary document is indexed into dataobs-ingest-summary per run.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, Iterator, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from elasticsearch import Elasticsearch, helpers

logger = logging.getLogger(__name__)

# ── helpers ────────────────────────────────────────────────────────────────

_RE_DATE = re.compile(
    r"^\d{4}-\d{2}-\d{2}"
    r"|^\d{2}/\d{2}/\d{4}"
    r"|^\d{2}-\w{3}-\d{4}$",
)
_RE_INT  = re.compile(r"^-?\d{1,15}$")
_RE_FLOAT= re.compile(r"^-?\d+\.\d+$")


def _infer_type(values: List[str]) -> str:
    """Infer ES field type from a sample of string values."""
    non_empty = [v for v in values if v and v.strip()]
    if not non_empty:
        return "keyword"
    if all(_RE_DATE.match(v.strip()) for v in non_empty[:20]):
        return "date"
    if all(_RE_INT.match(v.strip()) for v in non_empty[:20]):
        return "long"
    if all(_RE_FLOAT.match(v.strip()) for v in non_empty[:20]):
        return "double"
    if all(v.strip().lower() in {"true", "false", "yes", "no", "1", "0"} for v in non_empty[:20]):
        return "boolean"
    avg_len = sum(len(v) for v in non_empty[:50]) / len(non_empty[:50])
    return "keyword" if avg_len <= 128 else "text"


def _safe_field(name: str) -> str:
    """Sanitise a CSV header to a valid ES field name."""
    name = name.strip()
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_").lower()
    return name or "field"


def _infer_mapping(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build an ES properties mapping from a sample of parsed rows."""
    if not rows:
        return {}
    all_keys = list(rows[0].keys())
    properties: Dict[str, Any] = {
        "@timestamp": {"type": "date"},
        "dataset":    {"type": "keyword"},
        "run_id":     {"type": "keyword"},
        "theme":      {"type": "keyword"},
        "source_url": {"type": "keyword"},
        "row_index":  {"type": "long"},
    }
    sample = rows[:200]
    for key in all_keys:
        vals = [str(r.get(key, "") or "") for r in sample]
        properties[key] = {"type": _infer_type(vals)}
    return properties


def _download(url: str, timeout: int = 120) -> bytes:
    """Stream-download a URL (or read fixture file:// URI)."""
    logger.info("[etl] Downloading %s", url)
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return Path(parsed.path).read_bytes()
    if parsed.scheme in {"", "local"} and Path(url).exists():
        return Path(url).read_bytes()

    buf = io.BytesIO()
    resp = requests.get(url, stream=True, timeout=timeout,
                        headers={"User-Agent": "DataObs-POC/1.0"})
    resp.raise_for_status()
    total = 0
    chunk_size = 1 << 20
    for chunk in resp.iter_content(chunk_size=chunk_size):
        buf.write(chunk)
        total += len(chunk)
        if total % (10 * chunk_size) < chunk_size:
            logger.debug("[etl] Downloaded %.1f MB …", total / 1e6)
    logger.info("[etl] Download complete: %.2f MB", total / 1e6)
    return buf.getvalue()


def _detect_encoding(raw: bytes) -> str:
    try:
        import chardet
        result = chardet.detect(raw[:65536])
        return result.get("encoding") or "utf-8"
    except ImportError:
        return "utf-8"


def _parse_csv(raw: bytes, max_rows: int = 50_000) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Parse CSV bytes → (headers, rows-as-dicts)."""
    enc = _detect_encoding(raw)
    text = raw.decode(enc, errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return [], []
    headers = [_safe_field(h) for h in reader.fieldnames]
    rows: List[Dict[str, Any]] = []
    for i, row in enumerate(reader):
        if i >= max_rows:
            logger.warning("[etl] Truncating at %d rows (max_rows limit)", max_rows)
            break
        cleaned = {_safe_field(k): (v.strip() if v else None) for k, v in row.items()}
        rows.append(cleaned)
    return headers, rows


def _parse_json(raw: bytes, max_rows: int = 50_000) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Parse JSON bytes — handles top-level list or {data: [...]}."""
    enc = _detect_encoding(raw)
    payload = json.loads(raw.decode(enc, errors="replace"))
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        for key in ("data", "results", "items", "records", "features"):
            if isinstance(payload.get(key), list):
                records = payload[key]
                break
        else:
            records = [payload]
    else:
        records = []
    records = records[:max_rows]
    flat = []
    for rec in records:
        if isinstance(rec, dict):
            flat.append({_safe_field(k): v for k, v in rec.items()})
        else:
            flat.append({"value": rec})
    headers = list(flat[0].keys()) if flat else []
    return headers, flat


def _parse_xlsx(raw: bytes, max_rows: int = 50_000) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Parse XLSX bytes using openpyxl."""
    try:
        import openpyxl
    except ImportError:
        logger.warning("[etl] openpyxl not available — cannot parse XLSX")
        return [], []
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = iter(ws.rows)
    header_row = [_safe_field(str(cell.value or "")) for cell in next(rows_iter)]
    rows: List[Dict[str, Any]] = []
    for i, row in enumerate(rows_iter):
        if i >= max_rows:
            break
        rows.append({h: (cell.value) for h, cell in zip(header_row, row)})
    return header_row, rows


def parse_dataset(raw: bytes, fmt: str, max_rows: int = 50_000) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Dispatch to the correct parser based on fmt."""
    fmt = fmt.lower().lstrip(".")
    if fmt in {"csv", "tsv"}:
        return _parse_csv(raw, max_rows)
    if fmt in {"json", "geojson"}:
        return _parse_json(raw, max_rows)
    if fmt in {"xlsx", "xls"}:
        return _parse_xlsx(raw, max_rows)
    logger.warning("[etl] Unknown format '%s', attempting CSV parse", fmt)
    return _parse_csv(raw, max_rows)


# ── Elasticsearch helpers ──────────────────────────────────────────────────

def ensure_index(es: Elasticsearch, index: str, properties: Dict[str, Any]) -> None:
    """Create index with dynamic mapping + provided property hints if absent."""
    if es.indices.exists(index=index):
        return
    body: Dict[str, Any] = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "dynamic": "true",
            "properties": properties,
        },
    }
    es.indices.create(index=index, body=body)
    logger.info("[etl] Created index %s", index)


def _enrich(
    rows: List[Dict[str, Any]],
    *,
    dataset: str,
    run_id: str,
    theme: str,
    source_url: str,
    ts: str,
) -> Iterator[Dict[str, Any]]:
    """Add envelope fields to each row."""
    for i, row in enumerate(rows):
        doc = dict(row)
        doc.update(
            {
                "@timestamp": ts,
                "dataset":    dataset,
                "run_id":     run_id,
                "theme":      theme,
                "source_url": source_url,
                "row_index":  i,
            }
        )
        yield doc


def bulk_index(es: Elasticsearch, index: str, docs: Iterable[Dict[str, Any]]) -> int:
    """Bulk-index documents; return count of indexed docs."""
    actions = ({"_index": index, "_source": doc} for doc in docs)
    ok, errors = helpers.bulk(es, actions, chunk_size=500, raise_on_error=False,
                              stats_only=True)
    if errors:
        logger.warning("[etl] %d bulk errors in index %s", errors, index)
    logger.info("[etl] Indexed %d documents into %s", ok, index)
    return ok


# ── Public ETL API ─────────────────────────────────────────────────────────

class DatasetETL:
    """
    Download, parse, and ingest a single data source descriptor into ES.

    Parameters
    ----------
    es_host:      ES URL (default http://es01:9200)
    es_user:      ES username
    es_pass:      ES password
    index_prefix: prepended to the dataset name, default "dataobs-raw"
    max_rows:     maximum rows to ingest per dataset (default 50 000)
    """

    def __init__(
        self,
        es_host: str = "http://es01:9200",
        es_user: str = "elastic",
        es_pass: str = "changeme",
        index_prefix: str = "dataobs-raw",
        max_rows: int = 50_000,
    ) -> None:
        self.es = Elasticsearch(
            es_host,
            basic_auth=(es_user, es_pass),
            verify_certs=False,
            request_timeout=120,
        )
        self.index_prefix = index_prefix
        self.max_rows = max_rows

    def ingest_source(
        self,
        source: Dict[str, Any],
        run_id: str,
    ) -> Dict[str, Any]:
        """
        ETL one source descriptor (as produced by datasets.py).

        Returns a summary dict with keys: dataset, index, rows_ingested,
        columns, duration_seconds, status, error.
        """
        name       = source.get("name") or source.get("dataset_id") or "unknown"
        theme      = source.get("theme", "unknown")
        url        = source["resource_url"]
        fmt        = source.get("format", "csv")
        index      = f"{self.index_prefix}-{name}".lower().replace(" ", "-")
        ts         = datetime.now(timezone.utc).isoformat()
        t0         = time.time()
        result: Dict[str, Any] = {
            "dataset": name, "index": index, "theme": theme,
            "rows_ingested": 0, "columns": 0,
            "duration_seconds": 0.0, "status": "ok", "error": None,
        }
        try:
            raw = _download(url)
            headers, rows = parse_dataset(raw, fmt, self.max_rows)

            if not rows:
                logger.warning("[etl] No rows parsed from %s", url)
                result["status"] = "empty"
                return result

            result["columns"] = len(headers)
            logger.info("[etl] Parsed %d rows × %d cols from %s", len(rows), len(headers), name)

            properties = _infer_mapping(rows)
            ensure_index(self.es, index, properties)

            docs = list(_enrich(rows, dataset=name, run_id=run_id,
                                theme=theme, source_url=url, ts=ts))
            result["rows_ingested"] = bulk_index(self.es, index, docs)

        except Exception as exc:
            logger.error("[etl] Ingest failed for %s: %s", name, exc, exc_info=True)
            result["status"] = "error"
            result["error"]  = str(exc)

        result["duration_seconds"] = round(time.time() - t0, 2)
        return result

    def ingest_all(
        self,
        sources: List[Dict[str, Any]],
        run_id: str,
    ) -> List[Dict[str, Any]]:
        """ETL every source; return list of per-source summaries."""
        summaries = []
        for src in sources:
            logger.info("[etl] Starting ETL for dataset: %s", src.get("name", "?"))
            summary = self.ingest_source(src, run_id)
            summaries.append(summary)
            logger.info(
                "[etl] %s → %s  (%d rows, %.1fs, status=%s)",
                summary["dataset"], summary["index"],
                summary["rows_ingested"], summary["duration_seconds"],
                summary["status"],
            )
        return summaries

    def write_ingest_summary(
        self,
        summaries: List[Dict[str, Any]],
        run_id: str,
        tenant: str = "poc",
    ) -> None:
        """Write per-run summary document to dataobs-ingest-summary."""
        doc = {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id":     run_id,
            "tenant":     tenant,
            "datasets_attempted": len(summaries),
            "datasets_ok":    sum(1 for s in summaries if s["status"] == "ok"),
            "datasets_empty": sum(1 for s in summaries if s["status"] == "empty"),
            "datasets_error": sum(1 for s in summaries if s["status"] == "error"),
            "total_rows":     sum(s["rows_ingested"] for s in summaries),
            "sources":        summaries,
        }
        ensure_index(self.es, "dataobs-ingest-summary", {
            "@timestamp": {"type": "date"},
            "run_id":     {"type": "keyword"},
            "tenant":     {"type": "keyword"},
            "datasets_attempted": {"type": "integer"},
            "datasets_ok":        {"type": "integer"},
            "total_rows":         {"type": "long"},
        })
        self.es.index(index="dataobs-ingest-summary", document=doc)
        logger.info(
            "[etl] Ingest summary: %d/%d ok, %d total rows",
            doc["datasets_ok"], doc["datasets_attempted"], doc["total_rows"],
        )
