variable "cluster_name" {
  type = string
}

variable "region" {
  type = string
}

variable "kubernetes_version" {
  type = string
}

variable "domain" {
  type = string
}

variable "subdomain" {
  type = string
}

variable "letsencrypt_email" {
  type = string
}

variable "oauth_app_client_id" {
  type = string
}

variable "oauth_app_client_secret" {
  type      = string
  sensitive = true
}

variable "oauth_allowed_teams" {
  type = list(string)
  validation {
    condition     = alltrue([for t in var.oauth_allowed_teams : length(split(":", t)) == 2])
    error_message = "Each entry in oauth_allowed_teams must be in 'org:team' format."
  }
}

variable "node_groups" {
  type = list(object({
    name          = string
    instance_type = string
    disk_size_gb  = string
    min_size      = string
    max_size      = string
    desired_size  = string
  }))
}

variable "cluster_log_retention_days" {
  type = number
}

variable "custom_tags" {
  type = map(string)
}

variable "workspace_operator_namespace" {
  type = string
}

variable "workspace_router_namespace" {
  type = string
}

variable "workspace_operator_chart_version" {
  type = string
}

variable "traefik_crd_chart_version" {
  type = string
}

