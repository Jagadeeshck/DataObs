# Team 1 / Team 2 streaming schema handoff

Team 1 owns registry observation, streaming format compatibility, subject/resource/application binding, consumer exposure, and pathway overlays. Team 2 owns Data Contracts, contract lifecycle/enforcement, Data Products, dataset/column lineage, and CI/CD Change Gate decisions.

Team 1 reuses only public type-compatibility primitives where their semantics align; it does not force relational rules onto Avro, Protobuf, or JSON Schema. Change Gates may consume the pure `CompatibilityEvaluation` read contract or a future authenticated read endpoint. Team 1 consumes contract id/version, enforcement mode, status, and schema expectation through Team 2 public reads and performs no private writes.

Registry compatibility and contract compliance are separate response dimensions. Open questions are provider-authoritative Protobuf/JSON Schema coverage and a public intake contract for pre-deploy evaluation; until resolved, proposed raw schemas are not persisted.
