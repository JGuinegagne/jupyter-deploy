variable "combined_tags" {
  description = "Combined tags to apply to all resources."
  type        = map(string)
}

variable "postfix" {
  description = "The deployment-specific postfix to add to resource names."
  type        = string
}

variable "certs_secret_prefix" {
  description = "The prefix for the name of the AWS secret where TLS certificates are stored."
  type        = string
}
