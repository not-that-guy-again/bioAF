import click

from bioaf_cli.commands.deploy import deploy
from bioaf_cli.commands.destroy import destroy


@click.group()
@click.version_option(version="0.1.0", prog_name="bioaf")
def cli():
    """bioAF -- computational biology platform CLI."""
    pass


cli.add_command(deploy)
cli.add_command(destroy)

if __name__ == "__main__":
    cli()
