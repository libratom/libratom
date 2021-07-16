#!/usr/bin/env python
# pylint: disable=missing-docstring

import csv
import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

import click
import click_log

from libratom.cli import PATH_METAVAR
from libratom.cli.cli import set_log_level_from_verbose
from libratom.cli.utils import PathPath, validate_out_path
from libratom.lib.download import download_files

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


# Set configuration on the root logger
click_log.basic_config(logging.getLogger())


@click.command(context_settings=CONTEXT_SETTINGS)
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
    default=Path("media_types.json"),
    callback=validate_out_path,
    type=PathPath(resolve_path=True),
    help=f"Write the output to {PATH_METAVAR}.",
)
def download_media_type_files(out) -> None:
    """Download media type files from https://www.iana.org/ and write a JSON file of all media types."""

    media_types = []

    media_type_registries = [
        "application",
        "audio",
        "font",
        "image",
        "message",
        "model",
        "multipart",
        "text",
        "video",
    ]

    # CSV files to download
    urls = [
        f"https://www.iana.org/assignments/media-types/{registry}.csv"
        for registry in media_type_registries
    ]

    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        download_files(urls, directory, dry_run=False)

        for file in directory.glob("*.csv"):
            with file.open(newline="") as csvfile:
                reader = csv.reader(csvfile)

                # Use the first token (Name) in each row, skip headers
                # The split is to strip DEPRECATED/OBSOLETED/... mentions appended to the name
                for [name, *_] in reader:
                    if name != "Name":
                        media_types.append(f"{file.stem}/{name.split(maxsplit=1)[0]}")

    with out.open(mode="w") as f:
        json.dump(sorted(media_types), f, indent=4)


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    download_media_type_files()
