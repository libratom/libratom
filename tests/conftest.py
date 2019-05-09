# pylint: disable=missing-docstring,redefined-outer-name,stop-iteration-return
from pathlib import Path
from zipfile import ZipFile
import pytest
import requests


CACHED_DATA_DIR = Path('/tmp/libratom/test_data/')


@pytest.fixture(scope='session')
def enron_dataset_part003() -> Path:
    """
    Returns:
        A directory with one PST file:
        andrew_lewis_000_1_1.pst
    """

    name = 'andrew_lewis'
    files = ['andrew_lewis_000_1_1.pst']
    url = 'https://s3.amazonaws.com/edrm.download.nuix.com/RevisedEDRMv1/andrew_lewis.zip'
    path = CACHED_DATA_DIR / name

    if not path.exists():
        # Make the directories
        CACHED_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Fetch the zipped PST file
        response = requests.get(url)
        zipped_path = CACHED_DATA_DIR / f'{name}.zip'
        zipped_path.write_bytes(response.content)

        # Unzip and remove archive
        ZipFile(zipped_path).extractall(path=CACHED_DATA_DIR)
        zipped_path.unlink()

    # Confirm the files are there
    for filename in files:
        assert (path / filename).is_file()

    yield path


@pytest.fixture(scope='session')
def sample_pst_file(enron_dataset_part003) -> Path:
    """
    Returns:
        A PST file path
    """

    # Get the first PST file of this enron subset
    yield next(enron_dataset_part003.glob('*.pst'))
