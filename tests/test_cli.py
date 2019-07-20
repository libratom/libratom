# pylint: disable=missing-docstring,invalid-name

from pathlib import Path

import pytest

import libratom
from libratom.cli.cli import ratom
from tests.conftest import Expected


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
