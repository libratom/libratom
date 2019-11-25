#!/usr/bin/env python
# pylint: disable=missing-docstring

import csv
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

import click
import click_log

from libratom.lib.download import download_files
from libratom.cli.cli import set_log_level_from_verbose

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


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
def download_media_type_files() -> str:
    """Download media type files from https://www.iana.org/ and return a JSON list of all media types.
    """

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
        f"https://www.iana.org/assignments/media-types/{registry}.csv" for registry in media_type_registries
    ]

    with TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        download_files(urls, directory, dry_run=False)

        for file in directory.glob('*.csv'):
            with file.open(newline='') as csvfile:
                reader = csv.reader(csvfile, delimiter=' ', quotechar='|')
                for row in reader:
                    print(', '.join(row))


if __name__ == "__main__":
    download_media_type_files()
