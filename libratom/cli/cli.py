import click

from libratom.cli import PathPath
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def ratom():
    pass


@ratom.command(context_settings=CONTEXT_SETTINGS)
@click.option('-o', '--out', required=True, type=PathPath(), help='Output file')
def entities():
    click.echo('ok')
