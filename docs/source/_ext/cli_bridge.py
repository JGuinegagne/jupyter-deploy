import typer.main
from jupyter_deploy.cli.app import runner

cli = typer.main.get_command(runner.app)
