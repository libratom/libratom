# pylint: disable=missing-docstring,invalid-name,too-few-public-methods

import datetime
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, Union
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
from libratom.lib.constants import SPACY_MODELS
from libratom.lib.core import load_spacy_model, open_mail_archive
from libratom.lib.database import db_session_from_cmd_out
from libratom.lib.entities import process_message
from libratom.lib.utils import BodyType, cleanup_message_body
from libratom.models import Configuration, Entity, FileReport, Message


@contextmanager
def does_not_raise():
    yield


class Expected:
    """
    Result object type for parametrized tests. Expand as necessary...
    """

    def __init__(self, status: int, tokens: List[str], **kwargs):
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
        (["-i", "en_core_web_sm"], Expected(status=0, tokens=[])),
        (["-u", "en_core_web_sm"], Expected(status=0, tokens=[])),
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
    en_core_web_sm_3_1_0,  # pylint: disable=unused-argument
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
        assert session.query(Entity).count() == 188459

        # Verify count per entity type
        results = (
            session.query(Entity.label_, func.count(Entity.label_))
            .group_by(Entity.label_)
            .all()
        )

        assert results

        expected_counts = {
            "CARDINAL": 40646,
            "DATE": 8539,
            "EVENT": 104,
            "FAC": 310,
            "GPE": 10754,
            "LANGUAGE": 2,
            "LAW": 12537,
            "LOC": 225,
            "MONEY": 1411,
            "NORP": 604,
            "ORDINAL": 582,
            "ORG": 91004,
            "PERCENT": 750,
            "PERSON": 16960,
            "PRODUCT": 738,
            "QUANTITY": 240,
            "TIME": 2530,
            "WORK_OF_ART": 523,
        }

        for entity_type, count in results:
            assert expected_counts[entity_type] == count

        # Confirm spaCy model version for this job
        assert (
            session.query(Configuration)
            .filter_by(name="spacy_model_version")
            .one()
            .value
            == "3.1.0"
        )


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


def test_ratom_emldump(cli_runner, enron_dataset_part004, good_eml_export_input):
    expected = Expected(status=0, tokens=[])

    with tempfile.TemporaryDirectory() as tmpdir:
        params = [
            f"-l{enron_dataset_part004}",
            f"-o{tmpdir}",
            str(good_eml_export_input),
        ]

        dump_eml_files(params, None, cli_runner, expected)


def test_install_spacy_model():
    with patch("spacy.cli.download", new=MagicMock(side_effect=SystemExit)):
        # Pick a model not yet installed so spaCy tries to download it
        assert install_spacy_model(SPACY_MODELS.zh_core_web_sm) == -1
