# pylint: disable=missing-docstring,invalid-name,too-few-public-methods,misplaced-comparison-constant

from pathlib import Path
from typing import List

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import libratom
from libratom.cli.cli import ratom
from libratom.models.entity import Entity
from libratom.utils.database import db_session
from libratom.utils.entity_extraction import extract_entities, get_msg_count


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
        (["-v"], Expected(status=0, tokens=["nothing to do", "All done"])),
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
    assert len(files) == 1

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
        assert session.query(Entity).count() == 14283

        for entity in session.query(Entity)[:10]:
            assert str(entity)


def test_handle_spacy_download(enron_dataset_part001):
    files = enron_dataset_part001.glob("*.pst")

    assert 1 == extract_entities(
        files=files, destination=Path.cwd(), spacy_model_name="no_such_model"
    )


def test_get_msg_count(enron_dataset_part044):
    files = enron_dataset_part044.glob("*.pst")

    assert sum(get_msg_count(file) for file in files) == 558
