# Beta 1 release rehearsal

Dispatch `Beta 1 release candidate` with a full SHA, candidate version, and
`dry_run=true`. Retain its uniquely named Team 6 artifact and independently
inspect every gate. Team 1–5 artifacts must be produced for the same SHA; absent,
failed, cancelled, mismatched, or ambiguous evidence remains pending/failing.
Only repeat with `dry_run=false` after environment approval and all mandatory
gates pass. A rehearsal is not Beta certification or production certification.
