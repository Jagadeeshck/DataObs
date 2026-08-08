cluster_id   = "dataobs-reference"
region       = "us-east-1"
private_subnet_ids = ["subnet-reference-a", "subnet-reference-b", "subnet-reference-c"]
external_elasticsearch_connection_reference = "secret-provider://dataobs/elasticsearch"
otlp_endpoint_reference = "config://dataobs/otlp-gateway"
tags = { Environment = "example" }
