# CLI Reference

`jupyter-deploy` exposes the `jd` command (also available as `jupyter-deploy` or `jupyter deploy`)
for managing cloud deployments of interactive applications.

## Command Overview

| Command | Description |
|---------|-------------|
| `jd init` | Initialize a new project |
| `jd config` | Configure a project |
| `jd up` | Create or mutate your infrastructure to serve your app |
| `jd down` | Tear down all infrastructure of a project |
| `jd show` | Inspect variables and outputs |
| `jd history` | View deployment logs |
| `jd users` | Manage access to your app at user level |
| `jd teams` | Manage access to your app at team level |
| `jd organization` | Manage access to your app at organization level |
| `jd server` | Manage your servers |
| `jd host` | Manage your host |
| `jd projects` | Manage your jupyter-deploy projects |


## Full Command Reference

The complete CLI reference is auto-generated from the source code.

```{eval-rst}
.. click:: cli_bridge:cli
   :prog: jd
   :nested: full
```
