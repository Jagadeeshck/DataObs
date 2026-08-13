# Operating Post-Incident Reviews

Create reviews only for resolved or closed incidents. Assign an authenticated subject, submit for review, then complete with optimistic concurrency. A conflict requires reloading rather than overwriting. Refresh evidence explicitly when `source_changed` is shown. Never paste logs, SQL, credentials or provider bodies; attach evidence identifiers. Corrections to completed reviews require a new generation.
