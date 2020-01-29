# pylint: disable=unused-argument
"""
Command-line interface for libratom
"""

import logging
import sys
from pathlib import Path

import click
import click_log
import psutil

import libratom.cli.subcommands as subcommands
from libratom.cli import CONTEXT_SETTINGS, INT_METAVAR, PATH_METAVAR
from libratom.cli.utils import PathPath, validate_out_path
from libratom.lib.core import SPACY_MODEL_NAMES, SPACY_MODELS

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
        # Default
        level = logging.WARNING
    logging.getLogger().setLevel(level)
    return level


def cpu_count():
    """
    Return the number of available cores
    """

    # Use logical cores until this issue is fixed
    # https://github.com/giampaolo/psutil/issues/1620
    # return psutil.cpu_count(logical=False)
    return psutil.cpu_count(logical=True)


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
    "--spacy-model",
    help="Use a given spaCy model to extract entities.",
    type=click.Choice(SPACY_MODEL_NAMES),
    metavar="<model>",
    default=SPACY_MODELS.en_core_web_sm,
)
@click.option(
    "-j",
    "--jobs",
    metavar=INT_METAVAR,
    type=click.INT,
    help=f"Use {INT_METAVAR} concurrent jobs.",
    default=cpu_count(),
)
@click.argument(
    "src",
    metavar="[SOURCE]",
    default=Path.cwd,
    type=PathPath(exists=True, resolve_path=True),
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    callback=set_log_level_from_verbose,
    help="Increase verbosity (can be repeated).",
    expose_value=False,
)
@click.option("-p", "--progress", is_flag=True, help="Show progress.")
def entities(out, spacy_model, jobs, src, progress):
    """
    Extract named entities from a PST or mbox file, or a directory of one or more PST and mbox files.

    If SOURCE is a directory it will be walked recursively. Non-PST and non-mbox files will be skipped.

    If SOURCE is not provided the current working directory is used.

    Upon success the result will be a new .sqlite3 database file. If an output path is provided
    it will be either the output file's parent directory or the file itself.

    If no output path is provided the file will be written in the current working directory.
    """

    status = subcommands.entities(
        out=out, spacy_model_name=spacy_model, jobs=jobs, src=src, progress=progress
    )
    sys.exit(status)


@ratom.command(
    context_settings=CONTEXT_SETTINGS, short_help="Generate mailbox contents report."
)
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
    type=click.INT,
    help=f"Use {INT_METAVAR} concurrent jobs.",
    default=cpu_count(),
)
@click.argument(
    "src",
    metavar="[SOURCE]",
    default=Path.cwd,
    type=PathPath(exists=True, resolve_path=True),
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    callback=set_log_level_from_verbose,
    help="Increase verbosity (can be repeated).",
    expose_value=False,
)
@click.option("-p", "--progress", is_flag=True, help="Show progress.")
def report(out, jobs, src, progress):
    """
    ...
    """

    status = subcommands.report(out=out, jobs=jobs, src=src, progress=progress)
    sys.exit(status)
