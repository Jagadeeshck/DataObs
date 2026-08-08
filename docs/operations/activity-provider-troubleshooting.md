# Activity provider troubleshooting

Check the per-provider outcome before interpreting an empty feed. `timed_out` means the 2 second provider budget elapsed; `unavailable` means the safe summary read failed; `partial` means the capability returned incomplete evidence; and `permission_limited` is intentionally non-disclosing. Retry with the normal Console refresh after confirming tenant, environment and time range. Do not compensate with inventory downloads, broad queries or shortened polling intervals.
