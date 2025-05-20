# JupyterDeploy

Jupyter deploy provides a command line interface tool (CLI) that you can
use to deploy a Jupyter Server container to a remote compute provided by a Cloud provider.

## Install

From the repository root, run in order:

```bash
pip install -e ./libs/jupyter-deploy-tf-aws-ec2-ngrok
pip install -e ./libs/jupyter-deploy
```

### Install Terraform

Terraform from HashiCorp is the default deployment engine. To use it, you must set it up in your system.
Refer to Terraform installation [guide](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli).

Verify installation by running
```bash
terraform --version
```

## The CLI

To get started, open a terminal and run:

```bash
jupyter-deploy --help
```

## Templates

To use a template, use the following command format:

```bash
jupyter-deploy terraform generate --provider aws --infra ec2 --template tls-via-ngrok
```

## Contributing

Refer to the contributing guide.
