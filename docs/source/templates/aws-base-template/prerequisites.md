# Prerequisites

## AWS account
The template needs to create AWS resources. Your local environment needs access to valid AWS credentials.

If you do not have an AWS account, follow the [official guide](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-creating.html) to create one.

If you already have an AWS account, make sure your [CLI credentials are configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).

## Get and register a domain
The template serves your **JupyterLab** app to a URL in your own domain. You will need to specify this domain when you configure the project.

If you already own a domain, register it with Amazon Route 53 using this [guide](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/welcome-domain-registration.html).

If you do not own a domain yet, you can buy one through Amazon Route 53 using this [guide](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-register.html#domain-register-procedure-section).

## Setup a GitHub OAuth app

The template gates access to your **JupyterLab** application with GitHub identities. Log on to GitHub in your web browser, then create a new OAuth app using [this link](https://github.com/settings/applications/new). See the GitHub [documentation](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app) for details.

Next, configure the OAuth app:

| Field | Value |
|---|---|
| Application name | any, e.g. `jupyter-deploy-aws-base` |
| Homepage URL | `https://<subdomain>.<domain>` |
| Authorization callback URL | `https://<subdomain>.<domain>/oauth2/callback` |

```{note}
`<domain>` is your registered domain from above. Choose any `<subdomain>`, using lowercase letters, digits, or hyphens;
the callback URL must match both exactly.
```

Finally, save the **client ID**, generate a **client secret**, and save that too. You will need them to run `jd config`.
