# Operating the Elastic Workflows runtime

Workflow execution is disabled unless `DATAOBS_ELASTIC_WORKFLOWS_ENABLED=true`. Use a runtime credential limited to workflow read/run, execution read, and reviewed cancellation. The runtime polls only stored execution IDs with bounded backoff and requests neither input nor output by default. Report feature, license, forbidden, unreachable and unsupported-version capability states without converting them into generic server errors.
# Runtime certification

Workflow cancellation is disabled until the exact provider contract and privileges are certified. Managed Workflow
validation recursively inspects composite steps. Completion, verification, desired effect, and incident recovery are
separate states; provider completion never resolves an incident.
