# Support bundle

Run `python scripts/operations/collect_support_bundle.py INPUT OUTPUT --dry-run` before collection. The utility accepts only known JSON summaries, rejects unsafe/oversized input, recursively redacts sensitive keys and emits checksums plus a report. Verify locally, transfer only through an approved channel and retain access records. Never add Secrets, ConfigMaps, environment dumps, logs, documents, bodies or query text; the utility never uploads.
