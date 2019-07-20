# pylint: disable=missing-docstring,invalid-name,too-few-public-methods

from pathlib import Path
from typing import List

import pytest

import libratom
from libratom.cli.cli import ratom


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
    [(["-v"], Expected(status=0, tokens=["Creating database file", "All done"]))],
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
