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

from libratom.cli import (
    CONTEXT_SETTINGS,
    INT_METAVAR,
    MODEL_METAVAR,
    PATH_METAVAR,
    VERSION_METAVAR,
    subcommands,
)
from libratom.cli.utils import (
    PathPath,
    validate_eml_export_input,
    validate_existing_dir,
    validate_out_path,
    validate_version_string,
)
from libratom.lib.constants import ASCII_ART_NAME, SPACY_MODEL_NAMES, SPACY_MODELS

logger = logging.getLogger(__name__)

# Set configuration on the root logger
click_log.basic_config(logging.getLogger())


def set_log_level_from_verbose(ctx, param, value):
    """
    Callback for ratom subcommands that sets the root logger according to the verbosity option
    """
    if value > 1:
        level = logging.DEBUG
        click.echo(ASCII_ART_NAME)
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
    "-m",
    "--include-message-contents",
    is_flag=True,
    help="Also extract message headers and bodies.",
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
def entities(out, spacy_model, include_message_contents, jobs, src, progress):
    """
    Extract named entities from a PST or mbox file, or a directory of one or more PST and mbox files.

    If SOURCE is a directory it will be walked recursively. Non-PST and non-mbox files will be skipped.

    Upon success the result will be a new .sqlite3 database file. If an output path is provided
    it will be either the output file's parent directory or the file itself.

    If no output path is provided the file will be written in the current working directory.
    """

    status = subcommands.entities(
        out=out,
        spacy_model_name=spacy_model,
        jobs=jobs,
        src=src,
        include_message_contents=include_message_contents,
        progress=progress,
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
    "-m",
    "--include-message-contents",
    is_flag=True,
    help="Also extract message headers and bodies.",
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
def report(out, include_message_contents, jobs, src, progress):
    """
    Generate a report (file metadata, message count, and attachment metadata)
    from a PST or mbox file, or a directory of one or more PST and mbox files.

    If SOURCE is a directory it will be walked recursively. Non-PST and non-
    mbox files will be skipped.

    Upon success the result will be a new .sqlite3 database file. If an output
    path is provided it will be either the output file's parent directory or
    the file itself.

    If no output path is provided the file will be written in the current
    working directory.
    """

    status = subcommands.report(
        out=out,
        jobs=jobs,
        src=src,
        include_message_contents=include_message_contents,
        progress=progress,
    )
    sys.exit(status)


@ratom.command(context_settings=CONTEXT_SETTINGS, short_help="Manage spaCy models.")
@click.option(
    "-l", "--list", "_list", required=False, is_flag=True, help="List spaCy models."
)
@click.option(
    "-i",
    "--install",
    required=False,
    type=click.Choice(SPACY_MODEL_NAMES),
    metavar=MODEL_METAVAR,
    help=f"Install {MODEL_METAVAR}.",
)
@click.option(
    "-u",
    "--upgrade",
    required=False,
    type=click.Choice(SPACY_MODEL_NAMES),
    metavar=MODEL_METAVAR,
    help=f"Upgrade {MODEL_METAVAR}.",
)
@click.option(
    "--version",
    required=False,
    metavar=VERSION_METAVAR,
    callback=validate_version_string,
    help="If used alongside -i/--install, install a given model version. Otherwise this has no effect.",
)
def model(_list, install, upgrade, version):
    """
    Manage spaCy models.

    List, install, or upgrade currently installed models. Use the -i and --version
    flags together to install a previously released version of a specific model.
    """

    actions = [_list, install, upgrade]

    # Show help if no action option is passed
    if not any(actions):
        with click.get_current_context() as ctx:
            click.echo(ctx.get_help())
            sys.exit(0)

    # Error out if multiple actions are selected
    if [bool(x) for x in actions].count(True) > 1:
        raise click.UsageError(
            "Only one of [list|install|upgrade] can be selected at once."
        )

    status = subcommands.model(
        _list=_list, install=install, upgrade=upgrade, version=version
    )
    sys.exit(status)


@ratom.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Generate .eml files from pst/mbox files.",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    callback=set_log_level_from_verbose,
    help="Increase verbosity (can be repeated).",
    expose_value=False,
)
@click.option(
    "-o",
    "--out",
    metavar=PATH_METAVAR,
    default=Path.cwd,
    callback=validate_existing_dir,
    type=PathPath(resolve_path=True),
    help=f"Write .eml files in {PATH_METAVAR}.",
)
@click.option(
    "-l",
    "--location",
    metavar=PATH_METAVAR,
    default=Path.cwd,
    callback=validate_existing_dir,
    type=PathPath(resolve_path=True),
    help=f"Look for input files in {PATH_METAVAR}.",
)
@click.argument(
    "src",
    metavar="[SOURCE]",
    type=PathPath(exists=True, resolve_path=True),
    callback=validate_eml_export_input,
)
def emldump(out, location, src) -> None:
    """
    Generate .eml files from pst/mbox files.
    """

    status = subcommands.emldump(out=out, location=location, src=src)
    sys.exit(status)
