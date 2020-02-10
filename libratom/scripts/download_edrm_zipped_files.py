#!/usr/bin/env python
# pylint: disable=missing-docstring

import logging
from pathlib import Path

import click
import click_log

from libratom.cli.cli import set_log_level_from_verbose
from libratom.lib.download import download_files

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# From conftest.py
ENRON_DATASET_URL = "https://www.ibiblio.org/enron/RevisedEDRMv1_Complete"
CACHED_ENRON_DATA_DIR = Path("/tmp/libratom/test_data/RevisedEDRMv1_Complete")

# Set configuration on the root logger
click_log.basic_config(logging.getLogger())


@click.command(
    context_settings=CONTEXT_SETTINGS,
    help=f"Download edrm files into {CACHED_ENRON_DATA_DIR}/",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    callback=set_log_level_from_verbose,
    help="Increase verbosity (can be repeated).",
    expose_value=False,
)
def download_edrm_zipped_files() -> None:
    """Download edrm files into CACHED_ENRON_DATA_DIR.
    """

    names = [
        "albert_meyers",
        "andrea_ring",
        "andrew_lewis",
        "andy_zipper",
        "chris_dorland",
        "jason_wolfe",
        "vkaminski",
    ]

    # CSV files to download
    urls = [f"{ENRON_DATASET_URL}/{name}.zip" for name in names]

    download_files(urls, CACHED_ENRON_DATA_DIR, dry_run=False)


if __name__ == "__main__":
    download_edrm_zipped_files()
