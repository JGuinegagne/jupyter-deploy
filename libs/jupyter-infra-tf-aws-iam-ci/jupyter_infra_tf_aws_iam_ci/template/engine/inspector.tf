# Amazon Inspector2 enhanced scanning for ECR — account-wide.
# The CI account is single-purpose, so enabling Inspector here does not conflict
# with other deployments. This lets `jd image vulnerabilities` exercise the
# Inspector code path (OS + language-package CVEs, EPSS, continuous re-scan)
# in E2E tests rather than falling back to ECR basic scanning.
resource "aws_inspector2_enabler" "ecr" {
  account_ids    = [data.aws_caller_identity.current.account_id]
  resource_types = ["ECR"]
}
