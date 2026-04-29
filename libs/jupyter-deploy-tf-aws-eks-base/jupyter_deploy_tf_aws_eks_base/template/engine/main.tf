terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.30"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.14"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.9"
    }
  }
}

provider "aws" {
  region = var.region
}

provider "kubernetes" {
  host                   = module.eks_cluster.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks_cluster.cluster_ca_certificate)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks_cluster.cluster_name, "--region", var.region]
  }
}

provider "helm" {
  kubernetes = {
    host                   = module.eks_cluster.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks_cluster.cluster_ca_certificate)
    exec = {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks_cluster.cluster_name, "--region", var.region]
    }
  }
}

data "aws_region" "current" {}
data "aws_partition" "current" {}
data "aws_caller_identity" "current" {}

resource "random_id" "postfix" {
  byte_length = 4
}

locals {
  template_name    = "tf-aws-eks-base"
  template_version = "0.1.0"

  default_tags = {
    Source       = "jupyter-deploy"
    Template     = local.template_name
    Version      = local.template_version
    DeploymentId = random_id.postfix.hex
  }
  combined_tags        = merge(local.default_tags, var.custom_tags)
  resource_name_prefix = "${var.cluster_name}-${random_id.postfix.hex}"
}

data "aws_route53_zone" "domain" {
  name = var.domain
}

locals {
  full_domain         = var.subdomain != "" ? "${var.subdomain}.${var.domain}" : var.domain
  workspaces_base_url = "https://${local.full_domain}/workspaces"
}

module "vpc" {
  source               = "./modules/vpc"
  resource_name_prefix = local.resource_name_prefix
  combined_tags        = local.combined_tags
}

module "eks_cluster" {
  source                     = "./modules/eks_cluster"
  cluster_name               = var.cluster_name
  kubernetes_version         = var.kubernetes_version
  cluster_role_arn           = module.cluster_role.role_arn
  node_role_arn              = module.node_role.role_arn
  cluster_log_retention_days = var.cluster_log_retention_days
  vpc_id                     = module.vpc.vpc_id
  private_subnet_ids         = module.vpc.private_subnet_ids
  public_subnet_ids          = module.vpc.public_subnet_ids
  node_groups                = var.node_groups
  combined_tags              = local.combined_tags
}
