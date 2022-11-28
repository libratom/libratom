# pylint: disable=missing-docstring,invalid-name,protected-access
import datetime
import email
import hashlib
import logging
import os
import sys
import textwrap
from email import message_from_string, policy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import DEFAULT, MagicMock, Mock, patch

import pytest
from github import Github

import libratom
from libratom.data import MIME_TYPES
from libratom.lib.concurrency import get_messages
from libratom.lib.constants import SPACY_MODELS, BodyType
from libratom.lib.core import (
    get_cached_spacy_model,
    get_set_of_files,
    open_mail_archive,
)
from libratom.lib.database import db_init, db_session
from libratom.lib.download import download_files
from libratom.lib.entities import extract_entities, process_message
from libratom.lib.exceptions import FileTypeError
from libratom.lib.mbox import MboxArchive
from libratom.lib.pff import PffArchive
from libratom.lib.report import generate_report, get_file_info, scan_files
from libratom.lib.utils import cleanup_message_body
from libratom.models import FileReport

logger = logging.getLogger(__name__)


class BadPffFolder(MagicMock):
    """
    Mock folder class to simulate libpff errors
    """

    @property
    def number_of_sub_messages(self):
        raise OSError

    @property
    def sub_messages(self):
        raise OSError


def test_version():
    assert libratom.__version__


def test_pffarchive_load_from_file_object(sample_pst_file):

    with sample_pst_file.open(mode="rb") as f, PffArchive(f) as archive:
        assert len(list(archive.messages())) == 2668


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
                    # pylint: disable=no-member
                    if folder.identifier != archive._data.root_folder.identifier:
                        raise
                    continue
                if "sent mail" in name or "sent items" in name:
                    for message in folder.sub_messages:
                        assert message.transport_headers


def test_extract_message_attachments(enron_dataset_part002):
    """Checking 3 known attachments, to validate the attachment extraction process"""

    attachments = {
        47685: {
            "name": "cubicle hurdles.mpeg",
            "digest": "d48232614b01e56014293854abbb5db3",
        },
        47717: {
            "name": "Hallway races.mpeg",
            "digest": "cf8be7cd3e6e14307972246e2942c9d1",
        },
        47749: {
            "name": "Rowing.mpeg",
            "digest": "081e6b66dc89671ff6460adac94dbab1",
        },
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

            # Confirm attachment name
            assert att.name == attachments[att.identifier]["name"]

            # Confirm attachment checksum
            assert (
                hashlib.md5(rbuf).hexdigest() == attachments[att.identifier]["digest"]
            )

            # Sanity check on the file
            assert filepath.stat().st_size == att.size


def test_get_messages_with_bad_files(enron_dataset_part044, mock_progress_callback):

    _count = 0
    for _count, res in enumerate(
        get_messages(
            files=enron_dataset_part044.glob("*.pst"),
            progress_callback=mock_progress_callback,
        ),
        start=1,
    ):
        assert res

    assert _count == 558


def test_get_messages_with_bad_message(sample_pst_file, mock_progress_callback):

    _count = 0

    with patch.object(
        libratom.lib.pff.PffArchive, "get_attachment_metadata"
    ) as patched_method:

        # Raise on the first call, then don't raise
        def side_effects():
            yield RuntimeError
            while True:
                yield DEFAULT

        patched_method.side_effect = side_effects()

        for _count, res in enumerate(
            get_messages(
                files=[sample_pst_file],
                progress_callback=mock_progress_callback,
            ),
            start=1,
        ):
            assert res

    assert _count == 2667


def test_get_message_by_id(sample_pst_file):
    with PffArchive(sample_pst_file) as archive:
        for message in archive.messages():
            msg = archive.get_message_by_id(message.identifier)
            assert msg.identifier == message.identifier
            assert archive.format_message(msg) == archive.format_message(message)


def test_get_message_by_id_with_bad_id(sample_pst_file):
    with PffArchive(sample_pst_file) as archive:
        assert archive.get_message_by_id(1234) is None


def test_file_report_with_empty_relationship():
    file_report = FileReport()

    assert file_report.processing_start_time is None
    assert file_report.processing_end_time is None
    assert file_report.processing_wall_time is None


@pytest.mark.skipif(
    (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
    >= (3, 10, 0)
    and Github(os.environ.get("GITHUB_TOKEN"))
    .get_repo("pytorch/pytorch")
    .get_issue(number=66424)
    .state
    == "open",
    reason="https://github.com/pytorch/pytorch/issues/66424",
)
@pytest.mark.parametrize(
    "expected_entity_types",
    [{"DATE", "ORG", "PERSON", "QUANTITY"}],
)
def test_apply_transformer_model(
    sample_pst_file, en_core_web_trf_3_4_1, expected_entity_types
):
    model_name = en_core_web_trf_3_4_1.name

    # Extract a known (short) message
    msg_id = 2112164
    with open_mail_archive(sample_pst_file) as archive:
        msg_body = archive.get_message_body(archive.get_message_by_id(msg_id))[0]

    # Sanity check
    assert len(msg_body) == 564

    # Pre-load our model to install any missing dependencies
    assert get_cached_spacy_model(model_name)

    # Run worker function
    # pylint:disable=no-value-for-parameter
    res, error = process_message(
        # Must use dictionary form if function is called explicitly
        {
            "filepath": sample_pst_file,
            "message_id": msg_id,
            "date": datetime.datetime.utcnow(),
            "body": msg_body,
            "body_type": BodyType.PLAIN,
            "spacy_model_name": model_name,
            "attachments": None,
        }
    )

    assert res and not error

    # Check that the expected entity types were found
    assert expected_entity_types.issubset(set(entity[1] for entity in res["entities"]))


def test_extract_entities_from_mbox_files(directory_of_mbox_files):

    tmp_filename = "test.sqlite3"

    with TemporaryDirectory() as tmpdir:

        destination = Path(tmpdir) / tmp_filename
        Session = db_init(destination)

        with db_session(Session) as session:

            status = extract_entities(
                files=get_set_of_files(directory_of_mbox_files),
                session=session,
                spacy_model_name=SPACY_MODELS.en_core_web_sm,
                jobs=2,
            )

        assert status == 0


@pytest.mark.parametrize(
    "function, patched, kwargs",
    [
        (
            extract_entities,
            "libratom.lib.entities.Message",
            {
                "spacy_model_name": SPACY_MODELS.en_core_web_sm,
                "jobs": 2,
            },
        ),
        (generate_report, "libratom.lib.report.Message", {}),
    ],
)
def test_run_function_with_interrupt(
    directory_of_mbox_files, function, patched, kwargs
):

    tmp_filename = "test.sqlite3"

    with TemporaryDirectory() as tmpdir:

        destination = Path(tmpdir) / tmp_filename
        Session = db_init(destination)

        with db_session(Session) as session, patch(
            patched,
            new=MagicMock(side_effect=KeyboardInterrupt),
        ):

            status = function(
                files=get_set_of_files(directory_of_mbox_files),
                session=session,
                **kwargs,
            )

        assert status == 1


def test_scan_files_with_interrupt(directory_of_mbox_files):

    tmp_filename = "test.sqlite3"

    with TemporaryDirectory() as tmpdir:

        destination = Path(tmpdir) / tmp_filename
        Session = db_init(destination)

        with db_session(Session) as session, patch(
            "libratom.lib.report.FileReport",
            new=MagicMock(side_effect=KeyboardInterrupt),
        ):

            assert (
                scan_files(
                    files=get_set_of_files(directory_of_mbox_files),
                    session=session,
                    jobs=2,
                )
                == 1
            )


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

    bad_urls = ["http://foobar"] * 6

    with TemporaryDirectory() as tmpdir, patch("requests.Session.get") as mock_get:
        mock_get.return_value.ok = False

        with pytest.raises(RuntimeError):
            download_files(bad_urls, Path(tmpdir))


def test_utf8_message_with_no_cte_header_as_string():
    # Modified from https://github.com/python/cpython/blob/v3.10.8/Lib/test/test_email/test_email.py#L338
    # Confirm that the text is properly encoded and that an "8bit" CTE is added.
    msg = textwrap.dedent(
        """\
        MIME-Version: 1.0
        Test if non-ascii messages with no Content-Type nor
        Content-Transfer-Encoding set can be as_string'd:
        Föö bär
        """
    )

    expected = textwrap.dedent(
        """\
        MIME-Version: 1.0
        content-transfer-encoding: 8bit

        Test if non-ascii messages with no Content-Type nor
        Content-Transfer-Encoding set can be as_string'd:
        Föö bär
        """
    )

    assert MboxArchive.format_message(message_from_string(msg)) == expected


def test_get_file_info(sample_pst_file):

    res, error = get_file_info(
        # Must use dictionary form if function is called explicitly
        {"path": sample_pst_file}
    )

    assert res.get("path") == str(sample_pst_file)
    assert res.get("name") == sample_pst_file.name
    assert res.get("size") == 172450816
    assert res.get("md5") == "1038b99c2c323ca563da79dbbee3876f"
    assert (
        res.get("sha256")
        == "12c10d46f3935680f5c849a66737cf442fc171a2a20dce32c5efcc668366be96"
    )
    assert res.get("msg_count") == 2668
    assert not error


def test_attachments_mime_type_validation(enron_dataset, mock_progress_callback):

    files = get_set_of_files(enron_dataset)

    for res in get_messages(files, progress_callback=mock_progress_callback):
        attachments = res.get("attachments")
        if attachments:
            for attachment in attachments:
                try:
                    assert attachment.mime_type in MIME_TYPES
                except AssertionError:
                    # Some enron files have these obsolete attachment types
                    assert attachment.mime_type in [
                        "application/msexcell",
                        "application/mspowerpoint",
                    ]


def test_get_mbox_message_by_id(sample_mbox_file):
    with open_mail_archive(sample_mbox_file) as archive:

        assert archive.message_count == 113

        for index, message in enumerate(archive.messages(), start=1):
            msg = archive.get_message_by_id(index)
            assert msg
            assert archive.format_message(msg) == archive.format_message(message)
            assert archive.get_message_headers(message)


def test_get_mbox_message_by_id_with_bad_id(sample_mbox_file):
    with open_mail_archive(sample_mbox_file) as archive:
        assert archive.get_message_by_id(1234) is None


@pytest.mark.parametrize("mock_cls", [MagicMock, Mock])
def test_get_attachment_metadata(mock_cls):
    message = MagicMock(identifier=123, attachments=[mock_cls(name="foo", size="0")])

    assert PffArchive().get_attachment_metadata(message)[0].mime_type is None


@pytest.mark.parametrize(
    "message, body_type",
    [
        (Mock(), BodyType.PLAIN),
        (Mock(plain_text_body=None), BodyType.RTF),
        (Mock(plain_text_body=None, rtf_body=None), BodyType.HTML),
        (Mock(plain_text_body=None, rtf_body=None, html_body=None), None),
    ],
)
def test_get_message_body(message, body_type):
    assert PffArchive().get_message_body(message)[1] is body_type


@pytest.mark.parametrize(
    "body, body_type, result",
    [
        (
            r"{\rtf {\fonttbl {\f0 Times New Roman;}} \f0\fs60 foo} ",
            BodyType.RTF,
            "foo",
        ),
        ("<body><table><tr><td>foo</td></tr></table></body>", BodyType.HTML, "foo"),
    ],
)
def test_cleanup_message_body(body, body_type, result):
    assert cleanup_message_body(body, body_type) == result


def test_pff_archive_with_bad_folders(sample_pst_file):
    with PffArchive(sample_pst_file) as archive:
        with patch.object(archive, "folders") as mock_folders:
            mock_folders.return_value = [BadPffFolder()]

            # No uncaught exception
            assert archive.message_count == 0
            assert not list(archive.messages())
