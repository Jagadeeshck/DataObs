# Missing-run investigation

A run is missing only when interval, cron, external, or event-driven schedule evidence has sufficient confidence and the grace period has elapsed. Ad-hoc and unknown schedules remain `unknown`. Before escalation, verify `expected_at`, schedule source/confidence, paused state, maintenance window, last observed run, clock alignment, and scheduler health. Record the reason and attach direct scheduler evidence to any incident.
