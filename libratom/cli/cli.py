# pylint: disable=unused-argument,logging-fstring-interpolation
"""
Command-line interface for libratom
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import click
import click_log

from libratom.cli import (
    CONTEXT_SETTINGS,
    INT_METAVAR,
    PATH_METAVAR,
    PathPath,
    validate_in_path,
    validate_out_path,
)
from libratom.utils.entity_extraction import OUTPUT_FILENAME_TEMPLATE, extract_entities

logger = logging.getLogger(__name__)

# Set configuration on the root logger
click_log.basic_config(logging.getLogger())


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
@click.argument(
    "src",
    metavar="[SOURCE]",
    default=Path.cwd,
    type=PathPath(exists=True, resolve_path=True),
    callback=validate_in_path,
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    callback=set_log_level_from_verbose,
    help="Increase verbosity (can be repeated).",
)
@click.option("-p", "--progress", is_flag=True, help="Show progress.")
def entities(out, jobs, src, verbose, progress):
    """
    Extract named entities from a PST file or a directory of PST files.

    If SOURCE is a directory it will be walked recursively. Any non-PST file will be skipped.

    If SOURCE is not provided the current working directory is used.
    """

    status = 0

    # Resolve output file based on src parameter
    if out.is_dir():
        out = out / OUTPUT_FILENAME_TEMPLATE.format(
            src.name, datetime.now().isoformat(timespec="seconds")
        )

    # Get list of PST files from the source
    if src.is_dir():
        files = list(src.glob("**/*.pst"))
    else:
        files = [src]

    if not files:
        logger.warning(f"No PST file found in {src}; nothing to do")
    else:
        if progress:
            with click.progressbar(
                length=len(files), label="Processing files"
            ) as progress_bar:
                status = extract_entities(
                    files=files,
                    destination=out,
                    jobs=jobs,
                    log_level=verbose,
                    progress=progress_bar,
                )
        else:
            status = extract_entities(
                files=files, destination=out, jobs=jobs, log_level=verbose
            )

    logger.info("All done")
    sys.exit(status)
