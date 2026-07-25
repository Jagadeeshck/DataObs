# Job/run state machine

```mermaid
stateDiagram-v2
 [*] --> scheduled
 scheduled --> queued
 queued --> starting
 starting --> running
 running --> retrying
 retrying --> running
 running --> success
 running --> failed
 running --> timed_out
 running --> cancelled
 scheduled --> missing
```
Late START cannot regress a terminal projection. Duplicate events are idempotent. Conflicting terminal states retain the first deterministic projection unless an explicitly authorized correction is recorded; raw evidence remains append-only.
