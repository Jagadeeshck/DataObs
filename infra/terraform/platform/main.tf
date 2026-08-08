# Metadata-only reference contract. An organization-owned EKS module supplies resources.
locals {
  reference_inventory = {
    cluster_id             = var.cluster_id
    region                 = var.region
    private_subnet_count   = length(var.private_subnet_ids)
    architecture           = "aws-eks-private-multi-az"
    elasticsearch_external = true
    dataobs_installed_by   = "helm"
    tags                   = merge(var.tags, { ManagedFor = "DataObs", ArchitectureStatus = "unvalidated-reference" })
  }
}
