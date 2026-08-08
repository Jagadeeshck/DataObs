output "safe_reference_inventory" { value = local.reference_inventory }
output "elasticsearch_connection_reference" { value = var.external_elasticsearch_connection_reference; sensitive = true }
output "otlp_endpoint_reference" { value = var.otlp_endpoint_reference; sensitive = true }
