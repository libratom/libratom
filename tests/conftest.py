# pylint: disable=invalid-name,missing-docstring,redefined-outer-name,stop-iteration-return
import os
from pathlib import Path
from typing import List
from zipfile import ZipFile

import pytest
import requests

# Skip load tests
if not os.getenv("LIBRATOM_LOAD_TESTING"):
    collect_ignore_glob = ["load/*"]


CACHED_ENRON_DATA_DIR = Path("/tmp/libratom/test_data/RevisedEDRMv1_Complete")


def fetch_enron_dataset(name: str, files: List[str], url: str) -> Path:
    """Downloads and caches a given part of the Enron dataset archive (one per individual)

    Args:
        name: The individual's name
        files: A list of expected PST files
        url: The download URL for that file

    Returns:
        A directory path
    """
    path = CACHED_ENRON_DATA_DIR / name

    if not path.exists():
        # Make the directories
        CACHED_ENRON_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Fetch the zipped PST file
        response = requests.get(url)
        zipped_path = CACHED_ENRON_DATA_DIR / f"{name}.zip"
        zipped_path.write_bytes(response.content)

        # Unzip and remove archive
        ZipFile(zipped_path).extractall(path=CACHED_ENRON_DATA_DIR)
        zipped_path.unlink()

    # Confirm the files are there
    for filename in files:
        assert (path / filename).is_file()

    return path


@pytest.fixture(scope="session")
def enron_dataset_part002() -> Path:
    """
    Returns:
        A directory with one PST file:
        andrea_ring_000_1_1.pst
    """

    name = "andrea_ring"
    files = ["andrea_ring_000_1_1.pst"]
    url = (
        "https://s3.amazonaws.com/edrm.download.nuix.com/RevisedEDRMv1/andrea_ring.zip"
    )

    yield fetch_enron_dataset(name, files, url)


@pytest.fixture(scope="session")
def enron_dataset_part003() -> Path:
    """
    Returns:
        A directory with one PST file:
        andrew_lewis_000_1_1.pst
    """

    name = "andrew_lewis"
    files = ["andrew_lewis_000_1_1.pst"]
    url = (
        "https://s3.amazonaws.com/edrm.download.nuix.com/RevisedEDRMv1/andrew_lewis.zip"
    )

    yield fetch_enron_dataset(name, files, url)


@pytest.fixture(scope="session")
def enron_dataset_part004() -> Path:
    """
    Returns:
        A directory with two PST files:
        andy_zipper_000_1_1.pst
        andy_zipper_001_1_1.pst
    """

    name = "andy_zipper"
    files = ["andy_zipper_000_1_1.pst", "andy_zipper_001_1_1.pst"]
    url = (
        "https://s3.amazonaws.com/edrm.download.nuix.com/RevisedEDRMv1/andy_zipper.zip"
    )

    yield fetch_enron_dataset(name, files, url)


@pytest.fixture(scope="session")
def enron_dataset_part129() -> Path:
    """
    Returns:
        A directory with 7 PST files:
        vkaminski_000_1_1_1.pst
        vkaminski_001_1_1_1_1.pst
        vkaminski_001_1_2_1.pst
        vkaminski_001_1_2_2.pst
        vkaminski_002_1_1_1.pst
        vkaminski_003_1_1_1.pst
        vkaminski_003_1_1_2.pst
    """

    name = "vkaminski"
    files = [
        "vkaminski_000_1_1_1.pst",
        "vkaminski_001_1_1_1_1.pst",
        "vkaminski_001_1_2_1.pst",
        "vkaminski_001_1_2_2.pst",
        "vkaminski_002_1_1_1.pst",
        "vkaminski_003_1_1_1.pst",
        "vkaminski_003_1_1_2.pst",
    ]
    url = "https://s3.amazonaws.com/edrm.download.nuix.com/RevisedEDRMv1/vkaminski.zip"

    yield fetch_enron_dataset(name, files, url)


@pytest.fixture(scope="session")
def enron_dataset() -> Path:
    """
    Returns:
        A directory path expected to contain individual enron directories
    """
    assert CACHED_ENRON_DATA_DIR.exists()

    yield CACHED_ENRON_DATA_DIR


@pytest.fixture(scope="session", params=list(CACHED_ENRON_DATA_DIR.glob("**/*.pst")))
def enron_dataset_file(request) -> Path:
    """
    Returns:
        An enron PST file (per parameter)
    """

    yield request.param


@pytest.fixture(scope="session")
def sample_pst_file(enron_dataset_part003) -> Path:
    """
    Returns:
        A PST file path
    """

    # Get the first PST file of this enron subset
    yield next(enron_dataset_part003.glob("*.pst"))


@pytest.fixture
def empty_message(mocker):
    """
    Returns:
        A mock message with empty components
    """

    message = mocker.Mock()
    for attr in ("plain_text_body", "html_body", "rtf_body", "transport_headers"):
        setattr(message, attr, "")

    yield message
