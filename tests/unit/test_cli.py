# pylint: disable=missing-docstring,invalid-name,too-few-public-methods

import datetime
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, List, Optional, Union
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner, Result
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

import libratom
from libratom.cli import subcommands
from libratom.cli.cli import ratom
from libratom.cli.utils import (
    install_spacy_model,
    list_spacy_models,
    validate_eml_export_input,
    validate_existing_dir,
    validate_version_string,
)
from libratom.lib.base import AttachmentMetadata
from libratom.lib.constants import SPACY_MODELS
from libratom.lib.core import load_spacy_model, open_mail_archive
from libratom.lib.database import db_session_from_cmd_out
from libratom.lib.entities import process_message
from libratom.lib.utils import BodyType, cleanup_message_body
from libratom.models import (
    Configuration,
    Entity,
    FileReport,
    HeaderField,
    HeaderFieldType,
    Message,
)


@contextmanager
def does_not_raise():
    yield


class Expected:
    """
    Result object type for parametrized tests. Expand as necessary...
    """

    def __init__(self, status: int, tokens: Iterable[str] = (), **kwargs):
        self.status = status
        self.tokens = tokens

        for key, value in kwargs.items():
            setattr(self, key, value)


def run_ratom_subcommand(
    cmd: str,
    options: List,
    args: Union[Path, str, None],
    runner: CliRunner,
    expected: Optional[Expected],
) -> Result:
    """
    Block of code to run a given ratom subcommand as part of a test
    """

    if not cmd:
        raise ValueError("Empty ratom subcommand string")

    subcommand = [cmd]
    subcommand.extend(options)

    if args:
        subcommand.append(str(args))

    result = runner.invoke(ratom, subcommand)

    if expected:
        assert result.exit_code == expected.status

        for token in expected.tokens:
            assert token in result.output

    return result


def extract_entities(
    options: List,
    args: Union[Path, str, None],
    runner: CliRunner,
    expected: Optional[Expected],
) -> Result:
    """
    Block of code to run an entity extraction job as part of a test
    """

    return run_ratom_subcommand("entities", options, args, runner, expected)


def generate_report(
    options: List,
    args: Union[Path, str, None],
    runner: CliRunner,
    expected: Optional[Expected],
) -> Result:
    """
    Block of code to run a reporting job as part of a test
    """

    return run_ratom_subcommand("report", options, args, runner, expected)


def manage_spacy_models(
    options: List,
    args: Union[Path, str, None],
    runner: CliRunner,
    expected: Optional[Expected],
) -> Result:
    """
    Block of code to run a model management job as part of a test
    """

    return run_ratom_subcommand("model", options, args, runner, expected)


def dump_eml_files(
    options: List,
    args: Union[Path, str, None],
    runner: CliRunner,
    expected: Optional[Expected],
) -> Result:
    """
    Block of code to run an eml dump job as part of a test
    """

    return run_ratom_subcommand("emldump", options, args, runner, expected)


@pytest.mark.parametrize(
    "params, expected",
    [
        ([], "Usage"),
        (["-h"], "Usage"),
        (["--help"], "Usage"),
        (["--version"], libratom.__version__),
    ],
)
def test_ratom(cli_runner, params, expected):

    result = cli_runner.invoke(ratom, args=params)
    assert result.exit_code == 0
    assert expected in result.output

    with pytest.raises(ValueError):
        db_session_from_cmd_out(result)


@pytest.mark.parametrize(
    "params, expected",
    [
        ([], Expected(status=2, tokens=["Usage"])),
        (["-h"], Expected(status=0, tokens=["Usage"])),
        (["-v", os.getcwd()], Expected(status=0, tokens=["No PST file found"])),
        (
            ["-o", Path(__file__)],
            Expected(status=2, tokens=["Invalid value", "already exists"]),
        ),
        (
            ["/wrong/input/path"],
            Expected(status=2, tokens=["Invalid value", "does not exist"]),
        ),
    ],
)
def test_ratom_entities(cli_runner, params, expected):
    extract_entities(params, None, cli_runner, expected)


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            ["-vvpm", "-j2"],
            Expected(status=0, tokens=["Creating database file", "All done"]),
        )
    ],
)
def test_ratom_entities_enron_001(
    isolated_cli_runner, enron_dataset_part001, params, expected
):
    msg_id = 2097572

    # Run entity extraction job with message content flag on
    result = extract_entities(
        params, enron_dataset_part001, isolated_cli_runner, expected
    )

    # Get message contents from DB
    with db_session_from_cmd_out(result) as session:
        msg = session.query(Message).filter_by(pff_identifier=msg_id).one()
        headers, body = msg.headers, msg.body

    # Access message directly and compare
    archive_file = list(enron_dataset_part001.glob("*.pst"))[0]
    with open_mail_archive(archive_file) as archive:
        message = archive.get_message_by_id(msg_id)
        assert cleanup_message_body(*archive.get_message_body(message)) == body
        assert archive.get_message_headers(message) == headers


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            ["-vvp", "-j2"],
            Expected(
                status=0,
                tokens=["Creating database file", "All done"],
                with_messages=False,
            ),
        ),
        (
            ["-vvpm", "-j2"],
            Expected(
                status=0,
                tokens=["Creating database file", "All done"],
                with_messages=True,
            ),
        ),
    ],
)
def test_ratom_report_enron_027(
    isolated_cli_runner, enron_dataset_part027, params, expected
):
    msg_id = 2390436

    result = generate_report(
        params, enron_dataset_part027, isolated_cli_runner, expected
    )

    with db_session_from_cmd_out(result) as session:
        # Verify total message count
        assert session.query(Message).count() == 9297

        # Get message contents from DB
        msg = session.query(Message).filter_by(pff_identifier=msg_id).one()
        headers, body = msg.headers, msg.body

        if expected.with_messages:
            # Access message directly and compare
            archive_file = list(enron_dataset_part027.glob("*.pst"))[0]
            with open_mail_archive(archive_file) as archive:
                message = archive.get_message_by_id(msg_id)
                assert cleanup_message_body(*archive.get_message_body(message)) == body
                assert archive.get_message_headers(message) == headers

        else:
            assert headers is None
            assert body is None


@pytest.mark.parametrize(
    "params, expected",
    [(["-v"], Expected(status=0, tokens=["No PST file found"]))],
)
def test_ratom_report_empty(isolated_cli_runner, params, expected):
    # Make new empty dir
    with tempfile.TemporaryDirectory() as dirname:
        generate_report(params, Path(dirname), isolated_cli_runner, expected)


@pytest.mark.parametrize(
    "params, expected",
    [
        ([], Expected(status=0, tokens=["Usage"])),
        (["-h"], Expected(status=0, tokens=["Usage"])),
        (
            ["-l"],
            Expected(
                status=0,
                tokens=["spaCy model", "installed version", "available versions"],
            ),
        ),
        (
            ["-i"],
            Expected(status=2, tokens=["Error: Option '-i' requires an argument."]),
        ),
        (
            ["-u"],
            Expected(status=2, tokens=["Error: Option '-u' requires an argument."]),
        ),
        (
            ["-li", "en_core_web_sm"],
            Expected(
                status=2,
                tokens=["Only one of [list|install|upgrade] can be selected at once."],
            ),
        ),
    ],
)
def test_ratom_model(cli_runner, params, expected):
    manage_spacy_models(params, None, cli_runner, expected)


@pytest.mark.parametrize(
    "params, expected",
    [
        (["-i", "en_core_web_sm"], Expected(status=0)),
        (["-u", "en_core_web_sm"], Expected(status=0)),
    ],
)
def test_ratom_model_install(cli_runner, params, expected):
    manage_spacy_models(params, None, cli_runner, expected)


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            ["-vvp", "-j2"],
            Expected(status=0, tokens=["Creating database file", "All done"]),
        )
    ],
)
def test_ratom_entities_from_mbox_files(
    isolated_cli_runner, directory_of_mbox_files, params, expected
):
    extract_entities(params, directory_of_mbox_files, isolated_cli_runner, expected)


@pytest.mark.skipif(
    not os.getenv("CI", None),
    reason="Keep local test runs reasonably short",
)
@pytest.mark.parametrize(
    "params, expected",
    [
        (
            ["-v", "-j2"],
            Expected(status=0, tokens=["Creating database file", "All done"]),
        )
    ],
)
def test_ratom_entities_enron_004(
    isolated_cli_runner,
    enron_dataset_part004,
    en_core_web_sm_3_4_1,  # pylint: disable=unused-argument
    params,
    expected,
):
    result = extract_entities(
        params, enron_dataset_part004, isolated_cli_runner, expected
    )

    with db_session_from_cmd_out(result) as session:

        # Sanity check
        for entity in session.query(Entity)[:10]:
            assert str(entity)

        # Verify total entity count
        assert session.query(Entity).count() == 216758

        # Verify count per entity type
        results = (
            session.query(Entity.label_, func.count(Entity.label_))
            .group_by(Entity.label_)
            .all()
        )

        assert results

        expected_counts = {
            "CARDINAL": 43484,
            "DATE": 8798,
            "EVENT": 69,
            "FAC": 360,
            "GPE": 6952,
            "LANGUAGE": 3,
            "LAW": 361,
            "LOC": 287,
            "MONEY": 1914,
            "NORP": 763,
            "ORDINAL": 613,
            "ORG": 122184,
            "PERCENT": 13135,
            "PERSON": 13235,
            "PRODUCT": 633,
            "QUANTITY": 253,
            "TIME": 3095,
            "WORK_OF_ART": 619,
        }

        for entity_type, count in results:
            assert expected_counts[entity_type] == count

        # Confirm spaCy model version for this job
        assert (
            session.query(Configuration)
            .filter_by(name="spacy_model_version")
            .one()
            .value
            == "3.4.1"
        )


@pytest.mark.parametrize(
    "command",
    ["entities", "report"],
)
@pytest.mark.parametrize(
    "params, expected_counts",
    [
        (
            [],
            {HeaderFieldType: 0, HeaderField: 0},
        ),
        (
            ["-m"],
            {HeaderFieldType: 145, HeaderField: 16144},
        ),
    ],
)
def test_ratom_commands_with_header_fields(
    isolated_cli_runner,
    enron_dataset_part001,
    en_core_web_sm_3_4_1,  # pylint: disable=unused-argument
    command,
    params,
    expected_counts,
):
    # All runs should be successful
    success = Expected(status=0)

    # Add verbose flag to get the DB file from cmd out
    result = run_ratom_subcommand(
        command, params + ["-v"], enron_dataset_part001, isolated_cli_runner, success
    )

    with db_session_from_cmd_out(result) as session:

        # Validate row counts for header field types and header fields
        for object_type, count in expected_counts.items():
            assert session.query(object_type).count() == count


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            ["-v", "-j2"],
            Expected(status=0, tokens=["Creating database file", "All done"]),
        )
    ],
)
def test_ratom_entities_eml_files(
    isolated_cli_runner,
    test_eml_files,
    en_core_web_sm_3_4_1,  # pylint: disable=unused-argument
    params,
    expected,
):
    # Bad date string in example13.eml but valid for entity extraction
    valid_eml_files = test_eml_files / "emails" / "rfc2822"

    result = extract_entities(params, valid_eml_files, isolated_cli_runner, expected)

    with db_session_from_cmd_out(result) as session:

        # Verify total entity count
        assert session.query(Entity).count() == 86

        # Verify count per entity type
        results = (
            session.query(Entity.label_, func.count(Entity.label_))
            .group_by(Entity.label_)
            .all()
        )

        assert results

        expected_counts = {
            "CARDINAL": 16,
            "DATE": 20,
            "FAC": 1,
            "GPE": 2,
            "LAW": 3,
            "MONEY": 1,
            "ORG": 4,
            "PRODUCT": 2,
            "PERSON": 29,
            "TIME": 13,
            "WORK_OF_ART": 5,
        }

        for entity_type, count in results:
            assert expected_counts[entity_type] == count


@pytest.mark.skipif(
    not os.getenv("CI", None),
    reason="Keep local test runs reasonably short",
)
@pytest.mark.parametrize(
    "params, expected",
    [
        (
            ["-vp", "-j2"],
            Expected(status=0, tokens=["Creating database file", "All done"]),
        )
    ],
)
def test_ratom_entities_enron_012_from_file(
    monkeypatch, isolated_cli_runner, enron_dataset_part012, params, expected
):

    subcommand = ["entities"]
    subcommand.extend(params)

    monkeypatch.setenv("RATOM_DB_COMMIT_BATCH_SIZE", "100")

    # Use file name as source
    files = list(enron_dataset_part012.glob("*.pst"))

    subcommand.append(str(files[0]))

    result = isolated_cli_runner.invoke(ratom, subcommand)
    assert result.exit_code == expected.status


def test_entities_with_bad_model(enron_dataset_part001):
    with tempfile.TemporaryDirectory() as tmpdir:
        assert 1 == subcommands.entities(
            out=Path(tmpdir),
            spacy_model_name="no_such_model",
            jobs=2,
            src=enron_dataset_part001,
            progress=False,
        )

    assert not load_spacy_model(spacy_model_name="no_such_model")


def test_file_report(enron_dataset_part012):
    file = sorted(enron_dataset_part012.glob("*.pst"))[1]

    with tempfile.TemporaryDirectory() as tmpdir:

        out = Path(tmpdir) / "entities.sqlite3"

        # Extract entities
        assert 0 == subcommands.entities(
            out=out,
            spacy_model_name=SPACY_MODELS.en_core_web_sm,
            jobs=2,
            src=file,
            progress=False,
        )

        # Connect to DB file
        engine = create_engine(f"sqlite:////{out}")
        session = sessionmaker(bind=engine)()

        # There should be one FileReport instance for this run
        file_report = session.query(FileReport).one()  # pylint: disable=no-member

        # Path
        assert file_report.path == str(file)

        # Name
        assert file_report.name == file.name

        # Size
        assert file_report.size == file.stat().st_size

        # Checksums
        assert file_report.md5 == "ac62843cff3232120bba30aa02a9fe86"
        assert (
            file_report.sha256
            == "1afa29342c6bf5f774e03b3acad677febd5b0d59ec05eb22dee2481c8dfd6b88"
        )

        # Processing times
        assert file_report.processing_end_time > file_report.processing_start_time
        assert file_report.processing_wall_time > datetime.timedelta(0)

        # Message count
        assert file_report.messages

        # Entity count
        assert file_report.entities


def test_process_message():
    # pylint:disable=no-value-for-parameter

    filepath, message_id = "/foo/bar", 1234
    res, error = process_message(
        # Must use dictionary form if function is called explicitly
        {
            "filepath": filepath,
            "message_id": message_id,
            "date": datetime.datetime.utcnow(),
            "body": "hello",
            "body_type": BodyType.PLAIN,
            "spacy_model_name": None,
            "attachments": None,
        }
    )

    assert res.get("filepath") == filepath
    assert res.get("message_id") == message_id
    assert res.get("entities") is None
    assert error


def test_list_spacy_models():
    assert list_spacy_models() == 0


@pytest.mark.parametrize(
    "value,context",
    [
        ("1.2.3", does_not_raise()),
        ("2.0", does_not_raise()),
        ("0.0a1", does_not_raise()),
        (None, does_not_raise()),
        ("foobar", pytest.raises(click.BadParameter)),
        ("1", pytest.raises(click.BadParameter)),
        (".5", pytest.raises(click.BadParameter)),
    ],
)
def test_validate_version_string(value, context):
    with context:
        assert validate_version_string(None, None, value) == value


@pytest.mark.parametrize(
    "value,context",
    [
        (Path.cwd(), does_not_raise()),
        (Path("/bad/path/"), pytest.raises(click.BadParameter)),
    ],
)
def test_validate_existing_dir(value, context):
    with context:
        assert validate_existing_dir(None, None, value) == value


def test_validate_eml_export_input(bad_eml_export_input):
    with pytest.raises(click.BadParameter):
        validate_eml_export_input(None, None, bad_eml_export_input)


def test_ratom_emldump_from_pff(
    cli_runner, enron_dataset_part004, good_eml_export_input
):
    with tempfile.TemporaryDirectory() as tmpdir:
        root_path = Path(tmpdir)
        params = [
            f"-l{enron_dataset_part004}",
            f"-o{tmpdir}",
            str(good_eml_export_input),
        ]

        # Run ratom emldump command
        dump_eml_files(params, None, cli_runner, Expected(status=0))

        # Confirm exported data
        expected = {
            "andy_zipper_000_1_1": {
                "2203588": [
                    AttachmentMetadata(
                        name="US Gas Stack & Website for New Version 121401.xls",
                        size=39936,
                    ),
                ],
                "2203620": [
                    AttachmentMetadata(name="AGA.xls", size=129024),
                ],
            },
            "andy_zipper_001_1_1": {
                "2174116": [
                    AttachmentMetadata(name="Positions_10_15.xls", size=23040),
                    AttachmentMetadata(name="Positions_10_16.xls", size=23040),
                    AttachmentMetadata(name="Positions_10_17.xls", size=23040),
                    AttachmentMetadata(name="Positions_10_18.xls", size=23040),
                    AttachmentMetadata(name="Positions_10_19.xls", size=23040),
                    AttachmentMetadata(name="Positions_10_22.xls", size=23552),
                    AttachmentMetadata(name="Positions_10_23.xls", size=23552),
                ]
            },
        }

        for file_dir, msg_dirs in expected.items():
            for msg_pff_identifier, attachments in msg_dirs.items():

                # Confirm eml file is there
                eml_file_path = root_path / file_dir / f"{msg_pff_identifier}.eml"
                assert eml_file_path.is_file()

                for attachment in attachments:

                    # Confirm attachment files are there
                    attachment_path = (
                        root_path
                        / file_dir
                        / f"{msg_pff_identifier}_attachments"
                        / attachment.name
                    )
                    assert attachment_path.is_file()
                    assert attachment_path.stat().st_size == attachment.size


def test_ratom_emldump_from_mbox(cli_runner, directory_of_mbox_files):

    ratom_emldump_input = [
        {
            "filename": "201901.mbox",
            "sha256": "70a405404fd766a...",
            "id_list": ["6", "7", "12", "19", "57", "62", "68", "85", "85", "104"],
        }
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        root_path = Path(tmpdir)

        # Make json input file
        json_file_path = root_path / "ratom_emldump_input.json"
        with json_file_path.open(mode="w", encoding="UTF-8") as json_file:
            json.dump(ratom_emldump_input, json_file)

        params = [
            f"-l{directory_of_mbox_files}",
            f"-o{tmpdir}",
            str(json_file_path),
        ]

        # Run ratom emldump command
        dump_eml_files(params, None, cli_runner, Expected(status=0))

        # Confirm exported data
        expected = {
            "201901": {
                "6": [
                    AttachmentMetadata(name="image001.png", size=5598),
                ],
                "7": [
                    AttachmentMetadata(name="image001.png", size=5598),
                ],
                "12": [
                    AttachmentMetadata(name="image001.png", size=5598),
                ],
                "19": [
                    AttachmentMetadata(name="image001.png", size=5598),
                ],
                "57": [
                    AttachmentMetadata(name="image001.png", size=5598),
                ],
                "62": [
                    AttachmentMetadata(name="httpd.conf", size=21138),
                ],
                "68": [
                    AttachmentMetadata(name="httpd.conf", size=21219),
                ],
                "85": [
                    AttachmentMetadata(name="meet.galex-713.eu.conf", size=2382),
                    AttachmentMetadata(name="prosody.cfg.lua", size=8705),
                ],
                "104": [
                    AttachmentMetadata(name="error.log_err", size=143406),
                ],
            },
        }

        for file_dir, msg_dirs in expected.items():
            for msg_id, attachments in msg_dirs.items():

                # Confirm eml file is there
                eml_file_path = root_path / file_dir / f"{msg_id}.eml"
                assert eml_file_path.is_file()

                for attachment in attachments:

                    # Confirm attachment files are there
                    attachment_path = (
                        root_path / file_dir / f"{msg_id}_attachments" / attachment.name
                    )
                    assert attachment_path.is_file()
                    assert attachment_path.stat().st_size == attachment.size


def test_install_spacy_model():
    with patch("spacy.cli.download", new=MagicMock(side_effect=SystemExit)):
        # Pick a model not yet installed so spaCy tries to download it
        assert install_spacy_model(SPACY_MODELS.zh_core_web_sm) == -1
