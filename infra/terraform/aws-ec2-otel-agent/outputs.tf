output "install_document_name" {
  description = "SSM document name for OTEL agent installation."
  value       = aws_ssm_document.otel_agent_install.name
}

output "configure_document_name" {
  description = "SSM document name for OTEL agent config rollout."
  value       = aws_ssm_document.otel_agent_configure.name
}

output "install_association_id" {
  description = "SSM association id for install document."
  value       = aws_ssm_association.install.association_id
}

output "configure_association_id" {
  description = "SSM association id for configure document."
  value       = aws_ssm_association.configure.association_id
}
