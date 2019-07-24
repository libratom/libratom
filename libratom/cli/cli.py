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
import enlighten

from libratom.cli import (
    CONTEXT_SETTINGS,
    INT_METAVAR,
    PATH_METAVAR,
    PathPath,
    validate_out_path,
)
from libratom.utils.entity_extraction import (
    OUTPUT_FILENAME_TEMPLATE,
    SPACY_MODEL_NAMES,
    SPACY_MODELS,
    extract_entities,
    get_msg_count,
)

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
    type=click.IntRange(min=1, max=128),
    help=f"Use {INT_METAVAR} concurrent jobs.",
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
    Extract named entities from a PST file or a directory of PST files.

    If SOURCE is a directory it will be walked recursively. Any non-PST file will be skipped.

    If SOURCE is not provided the current working directory is used.

    Upon success the result will be a new .sqlite3 database file. If an output path is provided
    it will be either the output file's parent directory or the file itself.

    If no output path is provided the file will be written in the current working directory.
    """

    status = 0

    # Progress bar manager
    progress_bars = enlighten.get_manager()

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

    # Get the total number of messages
    logger.info("Getting total message count")
    msg_count = 0
    if progress:
        with progress_bars.counter(
            total=len(files),
            desc="Initial file scan",
            unit="files",
            color="green",
            leave=False,
        ) as file_bar:
            for file in files:
                msg_count += get_msg_count(file)
                file_bar.update()
    else:
        for file in files:
            msg_count += get_msg_count(file)

    # Get messages and extract entities
    if not files:
        logger.warning(f"No PST file found in {src}; nothing to do")
    else:
        if progress:
            with progress_bars.counter(
                total=msg_count, desc="Extracting entities", unit="msg", color="green"
            ) as msg_bar:
                status = extract_entities(
                    files=files,
                    destination=out,
                    spacy_model_name=spacy_model,
                    jobs=jobs,
                    progress_callback=msg_bar.update,
                )
        else:
            status = extract_entities(
                files=files, destination=out, spacy_model_name=spacy_model, jobs=jobs
            )

    logger.info("All done")
    sys.exit(status)
