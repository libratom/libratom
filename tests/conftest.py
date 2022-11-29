# pylint: disable=invalid-name,missing-docstring,redefined-outer-name,stop-iteration-return,line-too-long
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Dict, List
from zipfile import ZipFile

import pytest
import requests
from requests.exceptions import ChunkedEncodingError, HTTPError

from libratom.cli.utils import get_installed_model_version, install_spacy_model
from libratom.lib.download import download_files

# Skip load tests
if not os.getenv("LIBRATOM_LOAD_TESTING"):
    collect_ignore_glob = ["load/*"]

ENRON_DATASET_URL = "https://www.ibiblio.org/enron/RevisedEDRMv1_Complete"
CACHED_ENRON_DATA_DIR = Path("/tmp/libratom/test_data/RevisedEDRMv1_Complete")
CACHED_HTTPD_USERS_MAIL_DIR = Path("/tmp/libratom/test_data/httpd-users")


@dataclass
class SpacyModel:
    name: str
    version: str


def fetch_enron_dataset(name: str, files: List[str], url: str) -> Path:
    """Downloads and caches a given part of the Enron dataset archive (one per individual)

    Args:
        name: The individual's name
        files: A list of expected PST files
        url: The download URL for that file

    Returns:
        A directory path
    """
    dataset_path = CACHED_ENRON_DATA_DIR / name

    if not dataset_path.exists():
        # Make the directories
        CACHED_ENRON_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Look for existing zipped PST file
        zipped_path = CACHED_ENRON_DATA_DIR / f"{name}.zip"  # Default if not exists
        for path in CACHED_ENRON_DATA_DIR.rglob("*.zip"):
            if path.name == f"{name}.zip":
                zipped_path = path
                break

        # Fetch data if needed
        if not zipped_path.exists():
            max_tries = 5
            for i in range(1, max_tries + 1):
                try:
                    response = requests.get(url, timeout=(6.05, 30))

                    if response.ok:
                        zipped_path.write_bytes(response.content)
                    else:
                        response.raise_for_status()

                    # success
                    break

                except (ChunkedEncodingError, HTTPError):
                    if i < max_tries:
                        time.sleep(i)
                    else:
                        raise

        # Unzip and remove archive
        with ZipFile(zipped_path) as archive:
            archive.extractall(path=CACHED_ENRON_DATA_DIR)
        zipped_path.unlink()

    # Confirm the files are there
    for filename in files:
        assert (dataset_path / filename).is_file()

    return dataset_path


@pytest.fixture(scope="session")
def enron_dataset_part001() -> Path:
    """
    Returns:
        A directory with one PST file:
        albert_meyers_000_1_1.pst
    """

    name = "albert_meyers"
    files = ["albert_meyers_000_1_1.pst"]
    url = f"{ENRON_DATASET_URL}/albert_meyers.zip"

    yield fetch_enron_dataset(name, files, url)


@pytest.fixture(scope="session")
def enron_dataset_part002() -> Path:
    """
    Returns:
        A directory with one PST file:
        andrea_ring_000_1_1.pst
    """

    name = "andrea_ring"
    files = ["andrea_ring_000_1_1.pst"]
    url = f"{ENRON_DATASET_URL}/andrea_ring.zip"

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
    url = f"{ENRON_DATASET_URL}/andrew_lewis.zip"

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
    url = f"{ENRON_DATASET_URL}/andy_zipper.zip"

    yield fetch_enron_dataset(name, files, url)


@pytest.fixture(scope="session")
def enron_dataset_part012() -> Path:
    """
    Returns:
        A directory with two PST files:
        chris_dorland_000_1_1_1.pst
        chris_dorland_001_1_1_1.pst
    """

    name = "chris_dorland"
    files = ["chris_dorland_000_1_1_1.pst", "chris_dorland_001_1_1_1.pst"]
    url = f"{ENRON_DATASET_URL}/chris_dorland.zip"

    yield fetch_enron_dataset(name, files, url)


@pytest.fixture(scope="session")
def enron_dataset_part027() -> Path:
    """
    Returns:
        A directory with one PST file:
        drew_fossum_000_1_1.pst
    """

    name = "drew_fossum"
    files = ["drew_fossum_000_1_1.pst"]
    url = f"{ENRON_DATASET_URL}/drew_fossum.zip"

    yield fetch_enron_dataset(name, files, url)


@pytest.fixture(scope="session")
def enron_dataset_part044() -> Path:
    """
    Returns:
        A directory with two PST files:
        jason_wolfe_000_1_1.pst
        jason_wolfe_000_1_2.pst
    """

    name = "jason_wolfe"
    files = ["jason_wolfe_000_1_1.pst", "jason_wolfe_000_1_2.pst"]
    url = f"{ENRON_DATASET_URL}/jason_wolfe.zip"

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
    url = f"{ENRON_DATASET_URL}/vkaminski.zip"

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


@pytest.fixture(scope="session")
def directory_of_mbox_files() -> Path:
    """
    Returns:
        A directory with multiple mbox files
    """

    url_template = (
        "https://mail-archives.apache.org/mod_mbox/httpd-users/20190{month}.mbox"
    )

    # path is our destination directory
    path = CACHED_HTTPD_USERS_MAIL_DIR

    # Look for existing directory
    if not path.is_dir():
        # Download 6 monthly mailing list digests
        urls = [url_template.format(month=i) for i in range(1, 7)]
        download_files(urls, path)

    # Confirm the files are there
    for i in range(1, 7):
        assert (path / f"20190{i}.mbox").is_file()

    yield path


@pytest.fixture(scope="session")
def test_eml_files() -> Path:
    """
    Returns:
        The root directory of sample .eml data, valid and invalid.

    Downloaded from https://github.com/mikel/mail/tree/d18a73b6042522b37c7798e26c19158982cdecc1/spec/fixtures/emails
    """
    zipped_path = Path(__file__).resolve().parent / "emails.zip"

    # Extract in temporary dir
    with ZipFile(zipped_path) as archive, TemporaryDirectory() as tmpdir:
        archive.extractall(path=tmpdir)
        yield Path(tmpdir)


@pytest.fixture(scope="session")
def sample_mbox_file(directory_of_mbox_files) -> Path:
    yield sorted(directory_of_mbox_files.glob("*.mbox"))[0]


@pytest.fixture(scope="session")
def mock_progress_callback() -> Callable:
    """
    Returns:
        A no-op function
    """

    yield lambda *_, **__: None


@pytest.fixture(scope="function")
def eml_export_input_json() -> List[Dict]:
    """
    Returns:
        A JSON object that complies to libratom/data/eml_dump_input.schema.json
    """

    yield [
        {
            "filename": "andy_zipper_000_1_1.pst",
            "sha256": "70a405404fd766a...",
            "id_list": ["2203588", "2203620", "2203652"],
        },
        {
            "filename": "andy_zipper_001_1_1.pst",
            "sha256": "70a405404fd766a...",
            "id_list": ["2133380", "2133412", "2133444", "2174116"],
        },
    ]


@pytest.fixture(scope="function")
def good_eml_export_input(eml_export_input_json) -> Path:

    with TemporaryDirectory() as tmpdir:
        json_file_path = Path(tmpdir) / "test.json"

        with json_file_path.open(mode="w", encoding="UTF-8") as json_file:
            json.dump(eml_export_input_json, json_file)

        yield json_file_path


@pytest.fixture(scope="function")
def bad_eml_export_input(eml_export_input_json) -> Path:

    del eml_export_input_json[0]["sha256"]

    with TemporaryDirectory() as tmpdir:
        json_file_path = Path(tmpdir) / "test.json"

        with json_file_path.open(mode="w", encoding="UTF-8") as json_file:
            json.dump(eml_export_input_json, json_file)

        yield json_file_path


@pytest.fixture(scope="function")
def en_core_web_sm_3_4_1() -> None:
    model, version = "en_core_web_sm", "3.4.1"

    existing_version = get_installed_model_version(model)

    # Install wanted version
    if existing_version != version:
        assert install_spacy_model(model, version) == 0

    yield SpacyModel(name=model, version=version)

    # Reinstall previous version
    if existing_version and existing_version != version:
        assert install_spacy_model(model, existing_version) == 0


@pytest.fixture(scope="function")
def en_core_web_trf_3_4_1() -> None:
    model, version = "en_core_web_trf", "3.4.1"

    existing_version = get_installed_model_version(model)

    # Install wanted version
    if existing_version != version:
        assert install_spacy_model(model, version) == 0

    yield SpacyModel(name=model, version=version)

    # Reinstall previous version
    if existing_version and existing_version != version:
        assert install_spacy_model(model, existing_version) == 0
