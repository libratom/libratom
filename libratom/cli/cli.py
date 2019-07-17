from pathlib import Path

import click

from libratom.cli import (CONTEXT_SETTINGS, INT_METAVAR, PATH_METAVAR,
                          PathPath, validate_out_path)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def ratom():
    pass


@ratom.command(context_settings=CONTEXT_SETTINGS, short_help='Extract named entities.')
@click.option('-o', '--out', metavar=PATH_METAVAR, default=Path.cwd, callback=validate_out_path,
              type=PathPath(resolve_path=True), help=f'Write the output to {PATH_METAVAR}.')
@click.option('-j', '--jobs', metavar=INT_METAVAR,
              type=click.IntRange(min=1, max=128), help=f'Use {INT_METAVAR} concurrent jobs.')
@click.argument('src', metavar='[SOURCE]', default=Path.cwd, type=PathPath(exists=True))
def entities(**kwargs):
    """
    Extract named entities from a PST file or a directory of PST files.

    If SOURCE is a directory it will be walked recursively. Any non-PST file will be skipped.

    If SOURCE is not provided the current working directory is used.
    """

    click.echo(kwargs)
