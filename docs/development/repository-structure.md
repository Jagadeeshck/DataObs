# Repository structure

- `src/api`: FastAPI/Uvicorn API surface, legacy compatibility routes, and `/api/v1` product APIs.
- `src/core`: shared product abstractions such as the six-pillar model.
- `packages/domain_model`: stable tenant-aware Pydantic domain contracts.
- `packages/elastic_store`: explicit Elasticsearch migration manifest, registry, and CLI.
- `services/collection_manager`: minimal collection control plane.
- `src/poc`, `config/*poc*`, and demo scripts: isolated POC assets, not product runtime.
