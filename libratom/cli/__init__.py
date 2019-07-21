# pylint: disable=unused-argument,too-few-public-methods
"""
Command-line interface for libratom
"""

from pathlib import Path

import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

PATH_METAVAR = "<path>"
INT_METAVAR = "<n>"


# https://github.com/pallets/click/issues/405#issuecomment-470812067
class PathPath(click.Path):
    """
    A Click path argument that returns a pathlib Path, not a string
    """

    def convert(self, value, param, ctx):
        return Path(super().convert(value, param, ctx))


def validate_out_path(ctx, param, value: Path) -> Path:
    """
    Callback for click commands that checks that an output file doesn't already exist
    """

    if value.is_file():
        raise click.BadParameter(f'File "{value}" already exists.')

    return value
