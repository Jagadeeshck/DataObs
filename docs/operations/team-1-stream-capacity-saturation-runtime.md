# Stream capacity runtime operations

Run capacity evaluation inside the existing Stream Intelligence worker: acquire and renew the scoped lease, load a
bounded evidence window, evaluate, append immutable evidence, update the current projection with Elasticsearch
sequence-number/primary-term OCC, then checkpoint. Alert on lease loss, stale evidence, reconciliation backlog, and
checkpoint failure. Replay the immutable evaluation idempotently; a stale fencing token must stop the worker.
