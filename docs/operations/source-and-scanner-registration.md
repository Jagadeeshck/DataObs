# Source and scanner registration

Register sources without clear-text credentials. Use `credential_ref`; endpoint metadata must not include passwords, tokens, API keys, or private keys. Register scanners, send heartbeats, create scan policies, retrieve tasks, ACK tasks, and submit synthetic schema snapshots through `/api/v1/scanners/{scanner_id}/tasks/{task_id}/results`.
