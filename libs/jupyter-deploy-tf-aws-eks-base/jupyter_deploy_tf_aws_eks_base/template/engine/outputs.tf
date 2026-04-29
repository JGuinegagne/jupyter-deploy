output "cluster_name" {
  value = module.eks_cluster.cluster_name
}

output "cluster_endpoint" {
  value = module.eks_cluster.cluster_endpoint
}

output "cluster_ca_certificate" {
  value     = module.eks_cluster.cluster_ca_certificate
  sensitive = true
}

output "region" {
  value = data.aws_region.current.id
}

output "deployment_id" {
  value = random_id.postfix.hex
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "workspace_operator_namespace" {
  value = var.workspace_operator_namespace
}

output "workspace_router_namespace" {
  value = var.workspace_router_namespace
}

output "workspace_base_url" {
  value = local.workspaces_base_url
}
