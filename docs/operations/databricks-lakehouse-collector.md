# Databricks Lakehouse collector operations

Start with the disabled synthetic example. Resolve OAuth references in the worker environment and grant only the selected
workspace objects. Enable system tables separately and provide one approved collector warehouse. Tune page/object/lookback,
overlap, statement, byte, and observation bounds downward before scheduling.

`workspace_mismatch` is fail-closed; access denial is isolated to its evidence family. Preview unavailability is partial,
not proof of workspace failure. Roll back by disabling the integration; no provider migration or remote mutation needs
rollback. Never enable SDK debug dumps. Team 0 still owns packaging, Team 2 owns canonical job/run/Spark projection, and
Team 5 owns onboarding. Live certification and complete Unity Catalog visibility are not claimed.
