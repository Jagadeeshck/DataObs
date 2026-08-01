# AWS data platform collector IAM starting template

This is a **starting template requiring customer security review**, not deployed Terraform. `sts:GetCallerIdentity`
is mandatory and cannot be resource-scoped. Add only the selected service statements; many list/describe APIs require
`Resource: "*"`, while tag/individual get APIs should be narrowed where AWS supports it.

```json
{"Version":"2012-10-17","Statement":[
 {"Sid":"Identity","Effect":"Allow","Action":"sts:GetCallerIdentity","Resource":"*"},
 {"Sid":"RDS","Effect":"Allow","Action":["rds:DescribeDBInstances","rds:DescribeDBClusters","rds:ListTagsForResource"],"Resource":"*"},
 {"Sid":"Glue","Effect":"Allow","Action":["glue:GetJobs","glue:GetJobRuns","glue:GetCrawlers","glue:ListWorkflows","glue:ListTriggers","glue:GetTags"],"Resource":"*"},
 {"Sid":"Athena","Effect":"Allow","Action":["athena:ListWorkGroups","athena:GetWorkGroup","athena:ListQueryExecutions","athena:GetQueryExecution"],"Resource":"*"},
 {"Sid":"EMRServerless","Effect":"Allow","Action":["emr-serverless:ListApplications","emr-serverless:GetApplication","emr-serverless:ListJobRuns","emr-serverless:GetJobRun"],"Resource":"*"},
 {"Sid":"MetricsOptional","Effect":"Allow","Action":["cloudwatch:GetMetricData","cloudwatch:ListMetrics"],"Resource":"*"}
]}
```

Optional AssumeRole permission should name only `arn:aws:iam::000000000000:role/DataObsReadOnly`. Its synthetic trust
policy is `{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::000000000000:role/DataObsRuntime"},"Action":"sts:AssumeRole","Condition":{"StringEquals":{"sts:ExternalId":"resolved-outside-config"}}}]}`.
CloudWatch and identity validation cannot be resource-scoped; several list APIs also require wildcard resources.
External IDs, role credentials and complete secret identifiers must not enter logs or persisted evidence.
