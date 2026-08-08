# Safe remediation runtime operations

The worker consumes at most 25 durable queued operations, claims via OCC/fencing, performs at most the catalogue retry count, and persists the provider reference before verification. Unknown executors fail closed. Operators must investigate expired leases and use provider lookup before changing uncertain state; never blindly requeue an accepted operation.

This repository supplies the runtime state machine but no certified provider executor at this baseline. Deployment and scheduling remain Team 0 responsibilities. Health must report queued count, oldest age and lease conflicts without tenant/incident metric dimensions.
