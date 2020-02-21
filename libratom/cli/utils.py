# pylint: disable=unused-argument,too-few-public-methods,arguments-differ,import-outside-toplevel
"""
Command-line interface utilities
"""

import json
import re
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Optional

import click
import pkg_resources
import requests
import spacy
from pkg_resources import DistributionNotFound
from tabulate import tabulate


class PathPath(click.Path):
    """
    A Click path argument that returns a pathlib Path, not a string

    https://github.com/pallets/click/issues/405#issuecomment-470812067
    """

    def convert(self, value, param, ctx):
        return Path(super().convert(value, param, ctx))


class MockContext(AbstractContextManager):
    """
    A no-op context manager for use in python 3.6 and newer
    It accepts an arbitrary number of keyword arguments and returns an object whose attributes are all None

    Modified from https://github.com/python/cpython/blob/v3.7.4/Lib/contextlib.py#L685-L703
    """

    def __init__(self, **__):
        pass

    def __getattribute__(self, item):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *excinfo):
        pass


def validate_out_path(ctx, param, value: Path) -> Path:
    """
    Callback for click commands that checks that an output file doesn't already exist
    """

    if value.is_file():
        raise click.BadParameter(f'File "{value}" already exists.')

    return value


def validate_version_string(ctx, param, value: Optional[str]) -> Optional[str]:
    """
    Callback for click commands that checks that version string is valid
    """

    if value is None:
        return None

    version_pattern = re.compile(r"\d+(?:\.\d+)+")

    if not version_pattern.match(value):
        raise click.BadParameter(value)

    return value


def get_installed_model_version(name: str) -> Optional[str]:
    """
    Return the version of an installed package
    """

    try:
        return pkg_resources.get_distribution(name).version
    except DistributionNotFound:
        return None


def list_spacy_models() -> int:
    """
    Print installed spaCy models
    """

    response = requests.get(
        url="https://api.github.com/repos/explosion/spacy-models/releases"
    )

    if not response.ok:
        return -1

    # Get name-version pairs
    releases = [
        release["name"].rsplit("-", maxsplit=1)
        for release in json.loads(response.content)
    ]

    # Sort them by version name
    releases.sort(key=lambda x: x[0])

    table = [["spaCy model", "installed version", "latest version"]]

    for name, version in releases:
        table.append([name, get_installed_model_version(name), version])

    print(tabulate(table, headers="firstrow"))

    return 0


def install_spacy_model(
    model: str, version: Optional[str] = None, upgrade=False
) -> int:
    """
    Install a given spaCy model
    """
    from spacy.cli.download import msg as spacy_msg

    # Check for existing version
    installed_version = get_installed_model_version(model)

    if not version and not upgrade and installed_version:
        click.echo(
            click.style(f"Model {model} already installed, version {installed_version}")
        )
        return 0

    # Download quietly
    spacy_msg.no_print = True

    version_suffix, direct_download = (f"-{version}", True) if version else ("", False)

    try:
        spacy.cli.download(f"{model}{version_suffix}", direct_download, "--quiet")
    except SystemExit:
        click.echo(
            click.style(
                f"Unable to install spacy model {model}{version_suffix}", fg="red"
            )
        )
        return -1

    return 0
