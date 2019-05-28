# pylint: disable=missing-docstring,invalid-name
import email
import hashlib
import logging
from email import policy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import libratom
from libratom.utils.pff import PffArchive

logger = logging.getLogger(__name__)


def test_version():
    assert libratom.__version__


@pytest.mark.parametrize("skip_tree, expected", [(False, True), (True, False)])
def test_pffarchive_load_from_file_object(sample_pst_file, skip_tree, expected):

    with sample_pst_file.open(mode="rb") as f, PffArchive(
        f, skip_tree=skip_tree
    ) as archive:
        assert len([message for message in archive.messages()]) == 2668
        assert bool(archive.tree) is expected


def test_pffarchive_load_from_invalid_type():

    with pytest.raises(TypeError):
        _ = PffArchive(1)


@pytest.mark.parametrize("bfs", [False, True])
def test_pffarchive_iterate_over_messages(sample_pst_file, bfs):

    with PffArchive(sample_pst_file) as archive:
        for message in archive.messages(bfs=bfs):
            assert message.plain_text_body


def test_pffarchive_format_message(enron_dataset_part004, empty_message):

    for pst_file in enron_dataset_part004.glob("*.pst"):
        with PffArchive(pst_file) as archive:
            for message in archive.messages():
                # The assertion here doesn't matter as much as
                # not getting an exception from python's email parsing module
                assert email.message_from_string(
                    archive.format_message(message), policy=policy.default
                ) or not archive.format_message(message)

    assert PffArchive.format_message(empty_message) == ""


def test_get_transport_headers_from_sent_items(enron_dataset_part004):

    for pst_file in enron_dataset_part004.glob("*.pst"):
        with PffArchive(pst_file) as archive:
            for folder in archive.folders():
                try:
                    name = folder.name.lower()
                except AttributeError:
                    if folder.identifier != archive.data.root_folder.identifier:
                        raise
                    continue
                if "sent mail" in name or "sent items" in name:
                    for message in folder.sub_messages:
                        assert message.transport_headers


def test_extract_message_attachments(enron_dataset_part002):
    """Checking 3 known attachments, to validate the attachment extraction process
    """

    digests = {
        47685: "d48232614b01e56014293854abbb5db3",
        47717: "cf8be7cd3e6e14307972246e2942c9d1",
        47749: "081e6b66dc89671ff6460adac94dbab1",
    }

    with PffArchive(
        next(enron_dataset_part002.glob("*.pst"))
    ) as archive, TemporaryDirectory() as tmp_dir:

        # Get message by ID
        node = archive.tree.get_node(2128676)
        message = node.data

        for att in message.attachments:
            # Read attachment as bytes
            rbuf = att.read_buffer(att.size)

            # Save attachment
            filepath = (
                Path(tmp_dir) / f"attachment_{message.identifier}_{att.identifier}"
            )
            filepath.write_bytes(rbuf)

            # Confirm checksum
            assert hashlib.md5(rbuf).hexdigest() == digests[att.identifier]

            # Sanity check on the file
            assert filepath.stat().st_size == att.size
