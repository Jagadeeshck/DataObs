# Google Pub/Sub collector least privilege

Use `roles/pubsub.viewer` and `roles/monitoring.viewer`. A tighter custom role may include only
`pubsub.topics.get/list`, `pubsub.subscriptions.get/list`, `resourcemanager.projects.get`, and
`monitoring.timeSeries.list`, `monitoring.metricDescriptors.get/list`.

Do not grant Pub/Sub admin, editor, publisher, or subscriber roles. The collector neither needs nor permits
`pubsub.subscriptions.consume`, topic publish/update/delete, subscription update/delete, or snapshot seek. OAuth scopes
are `https://www.googleapis.com/auth/pubsub` and `https://www.googleapis.com/auth/monitoring.read`; IAM remains the
authorization boundary. Credential material, access/refresh tokens, policies and IAM bindings are excluded from logs
and evidence.
