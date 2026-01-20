# AWS Secrets Manager secret to store TLS certificates from Let's Encrypt
# The certificates are stored and retrieved at runtime by the EC2 instance
# This allows certificate persistence across instance replacements (e.g., GPU switches)
resource "aws_secretsmanager_secret" "tls_certificates" {
  name_prefix = "${var.certs_secret_prefix}-${var.postfix}-"
  tags        = var.combined_tags

  description = "TLS certificates from Let's Encrypt - managed by jupyter-deploy."
}
