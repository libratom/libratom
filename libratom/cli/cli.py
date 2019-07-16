from pathlib import Path
import click
from libratom.cli import PathPath

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

FILE_METAVAR = '<file>'
DIR_METAVAR = '<directory>'
INT_METAVAR = '<n>'


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def ratom():
    pass


@ratom.command(context_settings=CONTEXT_SETTINGS)
@click.option('-o', '--out', metavar=FILE_METAVAR, default=Path.cwd, type=PathPath(),
              help=f'Save the output as {FILE_METAVAR}.')
@click.option('-i', '--in', metavar=DIR_METAVAR,
              default=Path.cwd, type=PathPath(exists=True, file_okay=False),
              help=f'Process files in {DIR_METAVAR}.')
@click.option('-j', '--jobs', metavar=INT_METAVAR,
              type=click.IntRange(min=1, max=128), help=f'Use {INT_METAVAR} concurrent jobs.')
def entities(**kwargs):
    click.echo(kwargs)
