# mypy: disable-error-code=name-defined
c = get_config()  # noqa

c.Application.log_level = "INFO"

c.ServerApp.root_dir = "/home/jovyan"
c.ServerApp.terminado_settings = {
    "shell_command": [
        "bash",
        "-c",
        "echo \"This is a pixi-managed environment, use 'pixi add --pypi' or 'pixi add' instead of 'pip'!\"; bash",
    ]
}
