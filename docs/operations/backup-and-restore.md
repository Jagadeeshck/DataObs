# Beta backup and restore contract

DataObs state consists of the `dataobs-*` indices and aliases plus the
`logs-dataobs.*`, `metrics-dataobs.*`, and `traces-dataobs.*` streams. The
operator creates the snapshot repository (a filesystem repository is suitable
only for isolated CI) and supplies its name; credentials are never accepted in
the scripts or examples.

The Elasticsearch principal needs cluster snapshot privileges and index read,
create, close, delete, and restore privileges for those patterns. Back up only
after the terminal migration is applied. During recovery, stop writers, isolate
or delete conflicting indices, restore without global cluster state, verify the
terminal migration, tenant-filtered documents, append-only streams, and current
projections, then restart writers. Provider secrets outside Elasticsearch,
registry content, and identity-provider state are not backed up.

`backup_dataobs.py` and `restore_dataobs.py` emit metadata-only, redaction-safe
reports. Hosted testing must additionally seed two tenants and prove neither is
visible through the other's authenticated queries. RPO and RTO are **unvalidated**;
this Beta contract is not production certification.
