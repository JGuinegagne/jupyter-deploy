# JupyterDeploy

This monorepo contains packages for deploying Jupyter applications to various cloud providers.

## Packages

- [jupyter-deploy](./libs/jupyter-deploy/README.md): Core package providing a command line interface tool (CLI) that you can use to deploy a Jupyter Server container to a remote compute provided by a Cloud provider.
- [jupyter-deploy-tf-aws-ec2-ngrok](./libs/jupyter-deploy-tf-aws-ec2-ngrok/README.md): A Terraform template for Jupyter deployment on AWS EC2.

### Installation

Run the following commands from the repository root to install each package from source.

```bash
# Execute in this order
pip install -e ./libs/jupyter-deploy-tf-aws-ec2-ngrok
pip install -e ./libs/jupyter-deploy
```

## Contributing

Refer to the [contributing guide](./CONTRIBUTING.md).

## License

This project is licensed under the [MIT License](LICENSE).
