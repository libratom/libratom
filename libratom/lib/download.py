# pylint: disable=invalid-name,missing-docstring
"""
Multithreaded download utilities
"""

import concurrent.futures
import logging
import threading
from pathlib import Path
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


thread_local = threading.local()


def get_session() -> requests.Session:
    try:
        return thread_local.session
    except AttributeError:
        thread_local.session = requests.Session()

        retries = Retry(total=10, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retries)
        thread_local.session.mount("https://", adapter)

        return thread_local.session


def download_file(
    url: str, download_dir: Path, dry_run: bool = False, force: bool = False
) -> int:
    path = download_dir / url.rsplit("/", 1)[1]

    session = get_session()
    thread_id = threading.current_thread().name

    written = 0

    if dry_run:
        logger.info(f"{thread_id}: NOT downloading {url} (dry run)")
        return written

    if path.exists() and not force:
        logger.info(f"{thread_id}: {path} already present")
        return written

    logger.info(f"{thread_id}: Downloading {url}")

    # https://requests.readthedocs.io/en/master/user/advanced/#timeouts
    response = session.get(url, timeout=(6.05, 30))
    if response.ok:
        written = path.write_bytes(response.content)
        logger.debug(f"{thread_id}: Wrote {written} bytes to {path}")
    else:
        written = -1
        logger.error(f"{thread_id}: Request error: {response.status_code}")

    return written


def download_files(
    urls: Iterable[str], destination: Path, force: bool = False, dry_run: bool = False
) -> None:
    # destination is the directory the files will be written into
    destination.mkdir(parents=True, exist_ok=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for written in executor.map(
            lambda url: download_file(url, destination, force=force, dry_run=dry_run),
            urls,
        ):
            # detect error in threads
            if written < 0:
                raise RuntimeError("Error downloading files")
