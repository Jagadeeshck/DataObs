# Beta deployment package

Beta package v1 comprises API, Console, Quality Worker, Scanner Worker, Monitor Runtime, Pathway Worker, Kafka Observer, optional OpenTelemetry Collector, and migration Job. Elasticsearch is external-only. Kibana, identity, ingress controller, Grafana Alloy, Collection Manager, demos and POCs are excluded. Chart/application version is 0.2.0 and terminal migration is `0021_lineage_analysis_explorer`.

The release manifest binds exact component digests, SBOM, signature, provenance and certification artifact. `render_helm_values.py` produces secret-free pins. Capability status remains `functional_unvalidated` until exact-commit hosted Kind and upgrade/rollback evidence is independently downloaded and verified; a local smoke run is not certification.
