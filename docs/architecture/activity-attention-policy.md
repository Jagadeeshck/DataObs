# Activity attention policy

Policy version 1.0 has no fallback heuristic. Incident backend `severity=critical` maps to `critical`; `severity=high` maps to `warning`. Other values are ordinary operational events. Rules reference the source capability and exact evidence field/value. Seen status never changes attention, acknowledgement, incident, finding, case, workflow, or remediation state.
