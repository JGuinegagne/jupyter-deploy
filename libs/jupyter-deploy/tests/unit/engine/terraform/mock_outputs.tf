# instance ID
output "instance_id" {
  description = "ID of the jupyter notebook."
  value       = aws_instance.jupyter_server.id
}

# AWS region
output "aws_region" {
  description = "Name of the AWS region."
  value       = data.aws_region.current.id
}

# Public URL (heredoc description)
output "public_url" {
  description = <<-EOT
    The public URL for accessing the server.

    Includes the subdomain and domain.
  EOT
  value       = "https://example.com"
}