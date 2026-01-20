output "secret_arn" {
  description = "ARN of the AWS Secret where TLS certificates are stored."
  value       = aws_secretsmanager_secret.tls_certificates.arn
}
