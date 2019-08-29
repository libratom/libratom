# pylint: disable=missing-docstring,invalid-name,too-few-public-methods,misplaced-comparison-constant,no-value-for-parameter

import datetime
import os
import tempfile
from pathlib import Path
from typing import List

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

import libratom
import libratom.cli.subcommands as subcommands
from libratom.cli.cli import ratom
from libratom.lib.database import db_session
from libratom.lib.entities import (
    SPACY_MODELS,
    count_messages_in_files,
    load_spacy_model,
    process_message,
)
from libratom.models.entity import Entity
from libratom.models.file_report import FileReport


class Expected:
    """
    Result object type for parametrized tests. Expand as necessary...
    """

    def __init__(self, status: int, tokens: List[str]):
        self.status = status
        self.tokens = tokens


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


@pytest.mark.parametrize(
    "params, expected",
    [
        ([], Expected(status=0, tokens=["nothing to do"])),
        (["-h"], Expected(status=0, tokens=["Usage"])),
        (["-v"], Expected(status=0, tokens=["nothing to do"])),
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

    subcommand = ["entities"]
    subcommand.extend(params)

    result = cli_runner.invoke(ratom, subcommand)
    assert result.exit_code == expected.status

    for token in expected.tokens:
        assert token in result.output


@pytest.mark.parametrize(
    "params, expected",
    [(["-vvp"], Expected(status=0, tokens=["Creating database file", "All done"]))],
)
def test_ratom_entities_enron_001(
    isolated_cli_runner, enron_dataset_part001, params, expected
):

    subcommand = ["entities"]
    subcommand.extend(params)
    subcommand.append(str(enron_dataset_part001))

    result = isolated_cli_runner.invoke(ratom, subcommand)
    assert result.exit_code == expected.status

    for token in expected.tokens:
        assert token in result.output


@pytest.mark.parametrize(
    "params, expected",
    [(["-v"], Expected(status=0, tokens=["Creating database file", "All done"]))],
)
def test_ratom_entities_enron_001_from_file(
    isolated_cli_runner, enron_dataset_part001, params, expected
):

    subcommand = ["entities"]
    subcommand.extend(params)

    # Use file name as source
    files = list(enron_dataset_part001.glob("*.pst"))

    subcommand.append(str(files[0]))

    result = isolated_cli_runner.invoke(ratom, subcommand)
    assert result.exit_code == expected.status

    for token in expected.tokens:
        assert token in result.output

    # Validate output file
    db_file = None
    for line in result.output.splitlines():
        if line.startswith("Creating database file:"):
            db_file = Path(line.rsplit(maxsplit=1)[1].strip())

    assert db_file.is_file()

    # Open DB session
    engine = create_engine(f"sqlite:///{db_file}")
    Session = sessionmaker(bind=engine)

    with db_session(Session) as session:
        # Sanity check
        for entity in session.query(Entity)[:10]:
            assert str(entity)

        # Verify total entity count
        assert session.query(Entity).count() == 14283

        # Verify count per entity type
        results = (
            session.query(Entity.label_, func.count(Entity.label_))
            .group_by(Entity.label_)
            .all()
        )
        expected_counts = {
            "CARDINAL": 1937,
            "DATE": 552,
            "EVENT": 8,
            "FAC": 45,
            "GPE": 315,
            "LAW": 18,
            "LOC": 20,
            "MONEY": 183,
            "NORP": 55,
            "ORDINAL": 56,
            "ORG": 8802,
            "PERCENT": 13,
            "PERSON": 1116,
            "PRODUCT": 39,
            "QUANTITY": 3,
            "TIME": 1098,
            "WORK_OF_ART": 23,
        }
        for entity_type, count in results:
            assert expected_counts[entity_type] == count


@pytest.mark.skipif(
    not os.getenv("CONTINUOUS_INTEGRATION", None),
    reason="Keep local test runs reasonably short",
)
@pytest.mark.parametrize(
    "params, expected",
    [(["-vp"], Expected(status=0, tokens=["Creating database file", "All done"]))],
)
def test_ratom_entities_enron_012_from_file(
    isolated_cli_runner, enron_dataset_part012, params, expected
):

    subcommand = ["entities"]
    subcommand.extend(params)

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
            jobs=None,
            src=file,
            progress=False,
        )

        # Connect to DB file
        engine = create_engine(f"sqlite:////{out}")
        session = sessionmaker(bind=engine)()

        # There should be one FileReport instance fir this run
        file_report = session.query(FileReport).one()

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
        assert len(file_report.messages) == 4131

        # Entity count
        assert len(file_report.entities) == 25309


def test_process_message():
    filepath, message_id = "/foo/bar", 1234
    res, error = process_message(
        # Must use dictionary form if function is called explicitly
        {
            "filepath": filepath,
            "message_id": message_id,
            "message": "hello",
            "spacy_model": None,
        }
    )

    assert res.get("filepath") == filepath
    assert res.get("message_id") == message_id
    assert res.get("entities") is None
    assert error


def test_count_messages_in_files(enron_dataset_part044):
    files = enron_dataset_part044.glob("*.pst")
    count, good_files = count_messages_in_files(files)

    assert count == 558
    assert len(good_files) == 1
