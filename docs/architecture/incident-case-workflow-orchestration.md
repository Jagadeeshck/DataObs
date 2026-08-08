# Incident, Case and Workflow orchestration

The Incident Workbench reads Case collaboration state independently of Workflow availability. Safe Remediation may run a reviewed Case-triage Workflow against an already-linked Case. DataObs supplies a bounded DTO, stores the exact provider execution ID, polls that execution with input/output excluded, and verifies the expected Case effect. Neither Cases nor Workflows can mutate DataObs incident lifecycle.
