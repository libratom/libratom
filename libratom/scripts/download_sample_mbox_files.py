#!/usr/bin/env python
# pylint: disable=missing-docstring,unused-argument

import logging
from pathlib import Path

import click
import click_log

from libratom.lib.download import download_files

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# From conftest.py
CACHED_HTTPD_USERS_MAIL_DIR = Path("/tmp/libratom/test_data/httpd-users")

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
    help=f"Download sample mbox files into {CACHED_HTTPD_USERS_MAIL_DIR}/",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    callback=set_log_level_from_verbose,
    help="Increase verbosity (can be repeated).",
    expose_value=False,
)
def download_sample_mbox_files() -> None:
    """Download sample mbox files, currently from the httpd users mail archive."""

    url_template = (
        "https://mail-archives.apache.org/mod_mbox/httpd-users/20190{month}.mbox"
    )

    # path is our destination directory
    path = CACHED_HTTPD_USERS_MAIL_DIR

    # Download 6 monthly mailing list digests
    urls = [url_template.format(month=i) for i in range(1, 7)]
    download_files(urls, path)


if __name__ == "__main__":
    download_sample_mbox_files()
