# pylint: disable=unused-argument,too-few-public-methods,arguments-differ,import-outside-toplevel,broad-except
"""
Command-line interface utilities
"""

import re
from contextlib import AbstractContextManager
from email import policy
from email.generator import Generator
from email.message import Message
from email.parser import Parser
from importlib import reload
from pathlib import Path
from typing import Iterable, Optional

import click
import pkg_resources
import pypff
import spacy
from packaging.version import parse
from tabulate import tabulate

from libratom.lib import MboxArchive
from libratom.lib.base import Archive
from libratom.lib.core import get_spacy_models, open_mail_archive


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
    except pkg_resources.DistributionNotFound:
        return None


def list_spacy_models() -> int:
    """
    Print installed spaCy models
    """

    releases = get_spacy_models()

    # Sort the results by version name
    releases = list(releases.items())
    releases.sort(key=lambda x: x[0])

    table = [["spaCy model", "installed version", "available versions"]]

    for name, versions in releases:
        table.append([name, get_installed_model_version(name), ", ".join(versions)])

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
            click.style(
                f"Model {model} already installed, version {installed_version}",
                fg="blue",
            )
        )
        click.echo(
            click.style(
                f"Please specify a version or run `ratom model --upgrade {model}` to upgrade to the latest version",
                fg="blue",
            )
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
                f"❌ Unable to install spacy model {model}{version_suffix}", fg="red"
            ),
            err=True,
        )
        return -1

    # Confirm installation
    try:
        reload(pkg_resources)
        installed_version = pkg_resources.get_distribution(model).version

    except Exception as exc:
        click.echo(
            click.style(
                f"❌ Unable to confirm model installation, error: {exc}", fg="red"
            ),
            err=True,
        )
        return -1

    if version and parse(version) != parse(installed_version):
        click.echo(
            click.style(
                f"❌ Installed model version {installed_version} and specified version {version} differ",
                fg="red",
            ),
            err=True,
        )
        return -1

    click.echo(
        click.style(f"✔ Installed {model}, version {installed_version}", fg="green")
    )
    return 0


def pff_msg_to_string(message: pypff.message) -> str:
    """
    Serializes a pff.message object to a string
    """

    headers = message.transport_headers or ""
    body = message.plain_text_body or ""

    if isinstance(body, bytes):
        body = str(body, encoding="utf-8", errors="replace")

    return f"{headers.strip()}\r\n\r\n{body.strip()}"


def extract_message_from_archive(archive: Archive, msg_id: int) -> Message:
    """
    Extracts a message from an open Archive object
    """

    msg = archive.get_message_by_id(msg_id)

    # mbox archive
    if isinstance(archive, MboxArchive):
        return msg

    # pst archive
    return Parser(policy=policy.default).parsestr(pff_msg_to_string(msg))


def export_messages_from_file(src_file: Path, msg_ids: Iterable[int], dest_folder: Path = Path.cwd()) -> None:
    """
    Writes .eml files in a destination directory given a mailbox file (PST or mbox) and a list of message IDs
    """

    with open_mail_archive(src_file) as archive:
        for msg_id in msg_ids:
            msg = extract_message_from_archive(archive, msg_id)

            with (dest_folder / f'{msg_id}.eml').open(mode='w') as eml_file:
                Generator(eml_file).flatten(msg)
