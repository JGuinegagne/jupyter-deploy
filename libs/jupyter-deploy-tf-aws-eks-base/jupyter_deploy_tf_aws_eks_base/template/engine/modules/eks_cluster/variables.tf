variable "cluster_name" {
  type = string
}

variable "kubernetes_version" {
  type = string
}

variable "cluster_role_arn" {
  type = string
}

variable "node_role_arn" {
  type = string
}

variable "cluster_log_retention_days" {
  type = number
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "public_subnet_ids" {
  type = list(string)
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

variable "combined_tags" {
  type = map(string)
}
