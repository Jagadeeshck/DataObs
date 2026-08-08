# Action approval runtime

Approval states are `requested`, `approved`, `rejected`, `expired`, `cancelled`, and `consumed`. A request binds one preview, incident and target revision, normalized payload fingerprint, catalogue/policy hash, requester, tenant and environment. It expires no later than its preview.

Requesters cannot decide their request, approvers require the method-aware decision permission, and an approver cannot execute the governed action. Decisions use projection revision/OCC and append immutable events. Approved records are consumed once while queueing; rejected, expired, cancelled and consumed records cannot be revived or reused.
