# pylint: disable=missing-docstring
import filecmp
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from importlib import resources
except ImportError:
    # backport version for Python 3.6
    import importlib_resources as resources

import pytest

from libratom import data
from libratom.scripts.get_media_type_list import download_media_type_files


@pytest.mark.parametrize(
    "params, expected",
    [
        (["-h"], "Usage"),
        (["--help"], "Usage"),
    ],
)
def test_get_media_type_list_cli(cli_runner, params, expected):

    result = cli_runner.invoke(download_media_type_files, args=params)
    assert expected in result.output


def test_validate_media_type_list(cli_runner):

    with TemporaryDirectory() as tmp_dir, resources.path(data, 'media_types.json') as existing_path:
        new_path = Path(tmp_dir) / "media_types.json"

        cli_runner.invoke(download_media_type_files, args=['-o', str(new_path)])
        assert filecmp.cmp(existing_path, new_path)
