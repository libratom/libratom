# pylint: disable=missing-docstring,invalid-name

import pytest

import libratom
from libratom.cli.cli import ratom


@pytest.mark.parametrize(
    "options, expected", [
        (' ', 'Usage'),
        ('-h', 'Usage'),
        ('--help', 'Usage'),
        ('--version', libratom.__version__),
    ]
)
def test_ratom(cli_runner, options, expected):

    result = cli_runner.invoke(ratom, [options])
    assert result.exit_code == 0
    assert expected in result.output
