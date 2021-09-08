# pylint: disable=missing-docstring
import filecmp
import os
from importlib import resources
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from libratom import data
from libratom.scripts.get_media_type_list import download_media_type_files


@pytest.mark.parametrize("params, expected", [(["-h"], "Usage"), (["--help"], "Usage")])
def test_get_media_type_list_cli(cli_runner, params, expected):

    result = cli_runner.invoke(download_media_type_files, args=params)
    assert expected in result.output


def test_validate_media_type_list(cli_runner):
    """
    This test will fail if the media types file is out of date
    """

    with TemporaryDirectory() as tmp_dir, resources.path(
        data, "media_types.json"
    ) as existing_media_types_file:
        new_media_types_file = Path(tmp_dir) / "media_types.json"

        cli_runner.invoke(
            download_media_type_files, args=["-o", str(new_media_types_file)]
        )

        # Prevent a IANA media types update from failing a CI build
        # Run the test for coverage but skip the assertion
        if os.getenv("CI", "").lower() != "true":
            assert filecmp.cmp(existing_media_types_file, new_media_types_file)
