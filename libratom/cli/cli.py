# pylint: disable=unused-argument
"""
Command-line interface for libratom
"""

import logging
from pathlib import Path

import click
import click_log

from libratom.cli import (CONTEXT_SETTINGS, INT_METAVAR, PATH_METAVAR,
                          PathPath, validate_out_path)
from libratom.entities import extract_entities

logger = logging.getLogger(__name__)
click_log.basic_config(logger)

# Use the same logging configuration for libratom and its children
click_log.basic_config(logging.getLogger('libratom'))


def set_log_level_from_verbose(ctx, param, value):
    """
    Callback for ratom subcommands that sets the root logger according to the verbosity option
    """
    if value > 1:
        level = logging.DEBUG
    elif value > 0:
        level = logging.INFO
    else:
        level = logging.WARNING
    logger.setLevel(level)
    return level


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option()
def ratom():
    """
    Main command
    """


@ratom.command(context_settings=CONTEXT_SETTINGS, short_help="Extract named entities.")
@click.option(
    "-o",
    "--out",
    metavar=PATH_METAVAR,
    default=Path.cwd,
    callback=validate_out_path,
    type=PathPath(resolve_path=True),
    help=f"Write the output to {PATH_METAVAR}.",
)
@click.option(
    "-j",
    "--jobs",
    metavar=INT_METAVAR,
    type=click.IntRange(min=1, max=128),
    help=f"Use {INT_METAVAR} concurrent jobs.",
)
@click.argument("src", metavar="[SOURCE]", default=Path.cwd, type=PathPath(exists=True))
@click.option('-v', '--verbose', count=True, callback=set_log_level_from_verbose,
              help="Increase verbosity (can be repeated).")
def entities(out, jobs, src, verbose):
    """
    Extract named entities from a PST file or a directory of PST files.

    If SOURCE is a directory it will be walked recursively. Any non-PST file will be skipped.

    If SOURCE is not provided the current working directory is used.
    """

    extract_entities(source=src, destination=out, jobs=jobs, log_level=verbose)
