# pylint: disable=missing-docstring,invalid-name,no-member
import email
import hashlib
import logging
import os
import tempfile
from email import policy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import libratom
from libratom.lib.concurrency import get_messages
from libratom.lib.core import get_set_of_files, open_mail_archive
from libratom.lib.database import db_init, db_session
from libratom.lib.download import download_files
from libratom.lib.entities import SPACY_MODELS, extract_entities, load_spacy_model
from libratom.lib.exceptions import FileTypeError
from libratom.lib.pff import PffArchive
from libratom.models.file_report import FileReport

logger = logging.getLogger(__name__)


def test_version():
    assert libratom.__version__


def test_pffarchive_load_from_file_object(sample_pst_file):

    with sample_pst_file.open(mode="rb") as f, PffArchive(f) as archive:
        assert len([message for message in archive.messages()]) == 2668


def test_pffarchive_load_from_invalid_type():

    with pytest.raises(TypeError):
        _ = PffArchive(1)


def test_open_mail_archive_with_unsupported_type():

    with pytest.raises(FileTypeError):
        _ = open_mail_archive(Path("bad_path"))


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


def test_get_messages_with_bad_files(enron_dataset_part044):

    _count = 0
    for _count, res in enumerate(
        get_messages(files=enron_dataset_part044.glob("*.pst")), start=1
    ):
        assert res

    assert _count == 558


def test_get_message_by_id(sample_pst_file):
    with PffArchive(sample_pst_file) as archive:
        for message in archive.messages():
            msg = archive.get_message_by_id(message.identifier)
            assert msg.identifier == message.identifier
            assert archive.format_message(msg) == archive.format_message(message)


def test_get_message_by_id_with_bad_id(sample_pst_file):
    with PffArchive(sample_pst_file) as archive:
        assert archive.get_message_by_id(1234) is None


def test_get_messages_with_bad_messages(enron_dataset_part012):

    _count = 0
    for _count, res in enumerate(
        get_messages(files=enron_dataset_part012.glob("*.pst")), start=1
    ):
        assert res

    assert _count == 11262


@pytest.mark.skipif(
    not os.getenv("CONTINUOUS_INTEGRATION", None)
    or os.getenv("TRAVIS_OS_NAME", None) == "osx",
    reason="Keep local test runs and OSX travis runs reasonably short",
)
def test_extract_entities_with_bad_messages(enron_dataset_part012):

    tmp_filename = "test.sqlite3"

    with tempfile.TemporaryDirectory() as tmpdir:

        destination = Path(tmpdir) / tmp_filename
        Session = db_init(destination)

        with db_session(Session) as session:

            status = extract_entities(
                files=enron_dataset_part012.glob("*.pst"),
                session=session,
                spacy_model=load_spacy_model(SPACY_MODELS.en_core_web_sm),
                jobs=2,
            )

        assert status == 0


def test_file_report_with_empty_relationship():
    file_report = FileReport()

    assert file_report.processing_start_time is None
    assert file_report.processing_end_time is None
    assert file_report.processing_wall_time is None


def test_extract_entities_from_mbox_files(directory_of_mbox_files):

    tmp_filename = "test.sqlite3"

    with tempfile.TemporaryDirectory() as tmpdir:

        destination = Path(tmpdir) / tmp_filename
        Session = db_init(destination)

        with db_session(Session) as session:

            status = extract_entities(
                files=get_set_of_files(directory_of_mbox_files),
                session=session,
                spacy_model=load_spacy_model(SPACY_MODELS.en_core_web_sm),
                jobs=2,
            )

        assert status == 0


@pytest.mark.parametrize("dry_run", [False, True])
def test_download_files(directory_of_mbox_files, dry_run):

    assert directory_of_mbox_files  # so that the files are already present

    # Try to re-download files already downloaded by the fixture
    url_template = (
        "https://mail-archives.apache.org/mod_mbox/httpd-users/20190{month}.mbox"
    )
    path = Path("/tmp/libratom/test_data/httpd-users")
    urls = [url_template.format(month=i) for i in range(1, 7)]
    download_files(urls, path, dry_run=dry_run)


def test_download_files_with_bad_urls():

    bad_urls = ["http://httpstat.us/404"] * 6

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(RuntimeError):
            download_files(bad_urls, Path(tmpdir))
