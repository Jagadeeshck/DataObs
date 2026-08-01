# Access conflict recovery

A 409/412 stops the operation. Refresh the binding, compare the original and current safe revision/fields, then explicitly review the intended change again. Never automatically merge or resubmit an access-control mutation. A newly reviewed attempt receives a new idempotency key. A 404 means the binding was removed or is outside the trusted scope.
