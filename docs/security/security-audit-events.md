# Security audit events

Authentication failures, permission/selector denials, signing-key refreshes, IAM mutations, and high-risk actions use `logs-dataobs.security-event-*`. Events contain stable reason codes, request/trace identifiers, pseudonymous subject, trusted context, roles and required permission. They never contain tokens, authorization headers, signatures, secrets, sensitive bodies, or full email addresses. IAM mutations fail when their required durable audit write cannot be confirmed; operational authentication denials may use bounded redacted logging.
