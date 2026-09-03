Access is authorized by **AWS IAM identity** — no browser sign-in, no stored secret. `jd proxy
connect-info` (run by `jd open` / `jd proxy start`) mints a short-lived, presigned
`sts:GetCallerIdentity` token; the `auth-sidecar` behind Traefik replays it to STS, checks the
`x-k8s-aws-id` deployment binding, and matches the returned principal against the allowlist. The
caller must be an IAM role or IAM user in this deployment's AWS account (root and federated identities
are rejected at plan time).
