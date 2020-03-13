#!/usr/bin/env python
# pylint: disable=missing-docstring

import json
import logging
from email import policy
from email.generator import Generator
from email.message import Message
from email.parser import Parser
from pathlib import Path
from tempfile import gettempdir
from typing import Iterable

import click
import click_log
import pypff

import libratom
from libratom.cli import PATH_METAVAR
from libratom.cli.cli import set_log_level_from_verbose
from libratom.cli.utils import PathPath, validate_out_path
from libratom.lib import MboxArchive
from libratom.lib.base import Archive
from libratom.lib.core import open_mail_archive

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


# Set configuration on the root logger
click_log.basic_config(logging.getLogger())


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
    default=Path.cwd,
    callback=validate_out_path,
    type=PathPath(resolve_path=True),
    help=f"Write .eml files in {PATH_METAVAR}.",
)
def export_eml_files(out) -> None:
    """Do stuff
    """

    click.echo(out)


if __name__ == "__main__":
    export_eml_files()
