# Jupyter Deploy AWS EC2 JupyterLab template

Terraform template that runs a **single-user JupyterLab** on a remote AWS EC2 instance,
reached from your laptop through the local `jupyter-deploy-client-proxy` over a pinned
self-signed TLS connection, authenticated with short-lived AWS-identity (STS) tokens.

**AWS credentials are the only prerequisite**.

```
jd init . -E terraform -P aws -I ec2 -T jupyterlab   # default template = aws:ec2:jupyterlab
jd config                                            # region, instance type, volume size
jd up                                                # provision instance + self-signed cert
jd open                                              # start the proxy and open the browser
```

## How it works

- **Data path:** the browser talks to a local proxy over `http://localhost`; the proxy
  talks to the instance's Traefik on `:443` over pinned self-signed TLS (the pin is on the
  cert, not the address, so a new public IP after a stop/start is a non-event).
- **Cert pin:** the instance generates a long-lived self-signed cert at boot (private key
  persisted on the EBS data volume) and publishes only the public PEM to an SSM parameter
  that `jd proxy connect-info` reads live.
- **Auth:** `jd proxy connect-info` mints a `k8s-aws-v1` STS-identity token; a ForwardAuth
  sidecar behind Traefik validates it (STS replay + ARN allowlist + `x-k8s-aws-id` binding).
  No shared secret is stored anywhere.
- **Network:** the security group allows inbound `:443` only (open to `0.0.0.0/0`); the access
  boundary is the pinned TLS cert plus the STS-identity token above, not the network layer.

## Managing access

The deploying identity is always authorized. To grant others (matched case-insensitively by bare
IAM name, scoped to this account), use the runtime commands — they recreate only the auth-sidecar
(~1-2s), leave JupyterLab running, and write the change back into the terraform variables so `jd up`
stays in sync:

- IAM **roles**: `jd teams add|remove|set|list <RoleName>...`
- IAM **users**: `jd users add|remove|set|list <name>...`

(`jd teams` → IAM roles, `jd users` → IAM users.) The `iam_role_names_allowlist` /
`iam_user_names_allowlist` variables are the source of truth — editing them and running `jd up` also
reconciles the allowlist, but restarts the whole app, so the commands above are preferred for routine
access changes. Because those commands write their change back into the variables, a later `jd up`
re-applies the same list rather than reverting it.

## New IAM permissions

The *local* CLI credentials need, in addition to the base SSM permissions:
`ec2:DescribeInstances`, `ec2:{Authorize,Revoke,Describe}SecurityGroupIngress`, and
`ssm:GetParameter` (to read the cert pin).

## License

MIT License. See [LICENSE](./LICENSE).
