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
 {"Sid":"S3Inventory","Effect":"Allow","Action":["s3:ListAllMyBuckets","s3:GetBucketLocation","s3:GetBucketVersioning","s3:GetEncryptionConfiguration","s3:GetBucketPublicAccessBlock","s3:GetObjectLockConfiguration","s3:GetLifecycleConfiguration","s3:GetReplicationConfiguration","s3:GetBucketLogging","s3:GetBucketTagging"],"Resource":"*"},
 {"Sid":"LambdaInventory","Effect":"Allow","Action":["lambda:ListFunctions","lambda:GetFunctionConfiguration","lambda:ListTags","lambda:GetFunctionConcurrency"],"Resource":"*"},
 {"Sid":"SageMakerInventory","Effect":"Allow","Action":["sagemaker:List*","sagemaker:Describe*","sagemaker:ListTags"],"Resource":"*"},
 {"Sid":"MWAAInventory","Effect":"Allow","Action":["airflow:ListEnvironments","airflow:GetEnvironment","airflow:ListTagsForResource"],"Resource":"*"},
 {"Sid":"RedshiftInventory","Effect":"Allow","Action":["redshift:DescribeClusters","redshift-serverless:ListNamespaces","redshift-serverless:ListWorkgroups","redshift-serverless:ListTagsForResource"],"Resource":"*"},
 {"Sid":"MetricsOptional","Effect":"Allow","Action":["cloudwatch:GetMetricData","cloudwatch:ListMetrics"],"Resource":"*"}
]}
```

Optional prefix sampling adds `s3:ListBucket`, narrowed to named synthetic bucket ARNs with an `s3:prefix` condition;
`s3:GetObject` is never required. Optional history adds only the listed SageMaker APIs and, after review,
`redshift-data:ListStatements`; it does not add credential retrieval or database connectivity. Optional CloudWatch is
the final statement. Inventory list APIs and CloudWatch require wildcard resources; individual APIs should be narrowed
when AWS supports it. Lambda code download, SageMaker artifact/notebook access, MWAA CLI-token/Airflow APIs, Redshift
credentials, and S3 object reads are deliberately absent.

Optional AssumeRole permission should name only `arn:aws:iam::000000000000:role/DataObsReadOnly`. Its synthetic trust
policy is `{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::000000000000:role/DataObsRuntime"},"Action":"sts:AssumeRole","Condition":{"StringEquals":{"sts:ExternalId":"resolved-outside-config"}}}]}`.
CloudWatch and identity validation cannot be resource-scoped; several list APIs also require wildcard resources.
External IDs, role credentials and complete secret identifiers must not enter logs or persisted evidence.
