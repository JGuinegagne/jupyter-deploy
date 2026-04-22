# Templates

`jupyter-deploy` uses **templates** to define what gets deployed and how.

A template targets a specific application, cloud provider and infrastructure-as-code engine.

It bundles the infrastructure-as-code files, configuration presets, and deployment logic
into a base project that you can deploy using simple `jd` commands.

## How Do Templates Work?

Templates register as Python entry points under `jupyter_deploy.terraform_templates`.
When you run `jd init <PROJECT-DIR>`, `jupyter-deploy` discovers available templates and lets you choose one.

`jupyter-deploy` will scaffold your project in your local `<PROJECT-DIR>` directory. You'll see something like:

```
<PROJECT-DIR>/
├── manifest.yaml       # Declares template metadata and provider commands
├── variables.yaml      # Variable definitions and configuration presets
├── AGENT.md            # Template-specific instructions for AI assistants
├── .gitignore
├── engine/             # Infrastructure-as-code files (e.g., Terraform .tf files)
└── services/           # Application service definitions and configurations
```

## Official Templates

```{toctree}
:maxdepth: 2

AWS Base Template <aws-base-template/index>
```

## The Default Template

If you do not specify a template when running `jd init PROJECT-DIR`, `jupyter-deploy` defaults to the **AWS Base Template**.

This template deploys a **JupyterLab** application to a dedicated Amazon EC2 instance, and serves it
to a dedicated URL in your own domain. It configures the application to control access using GitHub identities with the OAuth protocol.

- **Infrastructure-as-code Engine**: Terraform
- **Cloud Provider**: AWS
- **Identity**: GitHub OAuth

See the [**AWS Base Template**](aws-base-template/index) for full documentation.
