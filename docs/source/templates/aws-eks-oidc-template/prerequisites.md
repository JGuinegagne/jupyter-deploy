# Prerequisites

## AWS account

The template creates AWS resources (VPC, EKS cluster, node groups, IAM roles, ECR, Route 53 records).
Your local environment needs access to valid AWS credentials.

If you do not have an AWS account, follow the [official guide](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-creating.html) to create one.

If you already have an AWS account, make sure your [CLI credentials are configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).

## Get and register a domain

The template serves workspace URLs under a subdomain of your own domain. You will need to specify this domain when you configure the project.

If you already own a domain, register it with Amazon Route 53 using this [guide](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/welcome-domain-registration.html).

If you do not own a domain yet, you can buy one through Amazon Route 53 using this [guide](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-register.html#domain-register-procedure-section).

## Setup a GitHub OAuth app

The template gates access with GitHub identities. You grant access to **GitHub teams**, which must belong to your GitHub organization.

If you do not have a GitHub organization, you can create one using [this guide](https://docs.github.com/en/organizations/collaborating-with-groups-in-organizations/creating-a-new-organization-from-scratch).

```{note}
A personal app also works, but the organization may require
[third-party application approval](https://docs.github.com/en/organizations/managing-oauth-access-to-your-organizations-data/approving-oauth-apps-for-your-organization)
before it can read private membership.
```

Next, create a new OAuth app:
- for your organization:
`Settings` → `Developer settings` → `OAuth Apps` → `New OAuth App`
- for a personal app, log on to GitHub in your web browser, then use
[this link](https://github.com/settings/applications/new).

See the
GitHub [documentation](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app)
for details.

Next, configure your OAuth app:

| Field | Value |
|---|---|
| Application name | any, e.g. `jupyter-deploy-eks-oidc` |
| Homepage URL | `https://<subdomain>.<domain>` |
| Authorization callback URL | `https://<subdomain>.<domain>/dex/callback` |

Finally, save the **client ID**, generate a **client secret**, and save that too. You will need them to run `jd config`.

```{note}
The callback URL uses `/dex/callback` (not `/oauth2/callback` as in the base template),
because authentication goes through Dex as the OIDC identity provider. It must match
your `<subdomain>` and `<domain>` exactly.
```
