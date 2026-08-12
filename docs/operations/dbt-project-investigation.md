# dbt project investigation

Start with `/api/v1/dbt/projects`, then inspect a project and its bounded resources. Compare declared dependency evidence with runtime lineage; `declared_only` means runtime has not observed the edge, not that the edge is false. Treat exposures and semantic consumers as structurally or potentially affected unless direct failure evidence exists.

For tests, distinguish recurring consistent failure from intermittent transitions. Review missing health components before interpreting the numeric score. dbt contracts and effective DataObs Contracts are separate evidence and neither automatically mutates the other.
