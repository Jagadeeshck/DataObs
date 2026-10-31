#!/usr/bin/env python3
"""Execute empty secured ES -> terminal -> idempotent reapply; never delete resources."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from packages.elastic_store.client import make_client  # noqa: E402
from packages.elastic_store.manifest import migrations  # noqa: E402
from packages.elastic_store.registry import apply  # noqa: E402
from scripts.certification.provenance import certification_commit_sha  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    es = make_client()
    report = {
        "producer_sha": certification_commit_sha(),
        "status": "fail",
        "terminal_migration": migrations()[-1].migration_id,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        report["elasticsearch_version"] = es.info()["version"]["number"]
        assert report["elasticsearch_version"] == "9.5.5"
        # Prove auth is enforced, rather than merely supplying credentials.
        from elasticsearch import AuthenticationException, Elasticsearch

        try:
            Elasticsearch(os.environ["ELASTICSEARCH_URL"], ca_certs=os.environ["ELASTICSEARCH_CA_CERTS"]).info()
        except AuthenticationException:
            report["anonymous_rejected"] = True
        else:
            raise AssertionError("Elasticsearch allowed anonymous access")
        initial = dict(es.indices.get_mapping(index="dataobs-*", allow_no_indices=True))
        assert not initial, "a clean cluster is required; existing indices must never be deleted"
        report["mapping_before"] = initial
        expected = {m.migration_id: m.checksum for m in migrations()}
        first = apply(es)
        report["first_apply"] = "pass"
        report["mapping_after"] = dict(es.indices.get_mapping(index="dataobs-*"))
        second = apply(es)
        assert {m["migration_id"]: m["checksum"] for m in first} == expected
        assert {m["migration_id"]: m["checksum"] for m in second} == expected
        assert dict(es.indices.get_mapping(index="dataobs-*")) == report["mapping_after"]
        report.update(second_apply="pass", checksums=expected, status="pass")
    except Exception as exc:
        report["failure"] = str(exc)
        raise
    finally:
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
