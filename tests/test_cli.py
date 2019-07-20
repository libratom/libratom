# pylint: disable=missing-docstring,invalid-name

import pytest

import libratom
from libratom.cli.cli import ratom


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
        ([], ["nothing to do"]),
        (["-h"], ["Usage"]),
        (["-v"], ["nothing to do", "All done"]),
    ],
)
def test_ratom_entities(isolated_cli_runner, params, expected):

    args = ["entities"]
    args.extend(params)

    result = isolated_cli_runner.invoke(ratom, args=args)
    assert result.exit_code == 0

    for token in expected:
        assert token in result.output
