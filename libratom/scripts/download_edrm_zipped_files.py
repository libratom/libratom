#!/usr/bin/env python
# pylint: disable=missing-docstring,unused-argument

import logging
from pathlib import Path

import click
import click_log

from libratom.lib.download import download_files

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# From conftest.py
ENRON_DATASET_URL = "https://www.ibiblio.org/enron/RevisedEDRMv1_Complete"
CACHED_ENRON_DATA_DIR = Path("/tmp/libratom/test_data/RevisedEDRMv1_Complete")
EDRM_PART_NAME_MAPPING = {
    1: "albert_meyers",
    2: "andrea_ring",
    3: "andrew_lewis",
    4: "andy_zipper",
    12: "chris_dorland",
    44: "jason_wolfe",
    129: "vkaminski",
}

# Set configuration on the root logger
click_log.basic_config(logging.getLogger())


def set_log_level_from_verbose(ctx, param, value):
    if value > 1:
        level = logging.DEBUG
    elif value > 0:
        level = logging.INFO
    else:
        # Default
        level = logging.WARNING
    logging.getLogger().setLevel(level)
    return level


@click.command(
    context_settings=CONTEXT_SETTINGS,
    help=f"Download edrm files into {CACHED_ENRON_DATA_DIR}/",
)
@click.option(
    "-n",
    "--part-number",
    required=False,
    type=click.Choice([str(key) for key in EDRM_PART_NAME_MAPPING.keys()]),
    help="Download the given part number. If this is not provided, download the entire Enron dataset.",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    callback=set_log_level_from_verbose,
    help="Increase verbosity (can be repeated).",
    expose_value=False,
)
def download_edrm_zipped_files(part_number) -> None:
    """Download EDRM Enron files into CACHED_ENRON_DATA_DIR."""

    if part_number:
        urls = [f"{ENRON_DATASET_URL}/{EDRM_PART_NAME_MAPPING[int(part_number)]}.zip"]
    else:
        urls = [
            f"{ENRON_DATASET_URL}/{name}.zip"
            for name in EDRM_PART_NAME_MAPPING.values()
        ]

    download_files(urls, CACHED_ENRON_DATA_DIR, dry_run=False)


if __name__ == "__main__":
    download_edrm_zipped_files()
