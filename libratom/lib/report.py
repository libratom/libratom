# pylint: disable=broad-except
"""
Set of utility functions to generate job related reports
"""

import hashlib
import logging
import multiprocessing
from functools import partial
from pathlib import Path
from typing import Callable, Iterable, Tuple

from sqlalchemy.orm.session import Session

from libratom.lib.concurrency import imap_job, worker_init

logger = logging.getLogger(__name__)


@imap_job
def get_file_info(path: Path) -> Tuple:
    """
    For a given file path, returns the size, md5 and sha256 checksums
    """

    try:
        size = path.stat().st_size

        md5 = hashlib.md5()
        with open(str(path), "rb") as f:
            for block in iter(partial(f.read, 128), b''):
                md5.update(block)

        md5 = md5.hexdigest()


    except Exception as exc:
        return None, None, str(exc)

    return size, md5, None


def store_file_reports_in_db(
    files: Iterable[Path],
    session: Session,
    jobs=None,
    progress_callback: Callable = None,
) -> int:
    """
    Computes checksums from a list of files and record them in a database via an ORM session object
    """

    # Start of multiprocessing
    with multiprocessing.Pool(processes=jobs, initializer=worker_init) as pool:

        print(f"Starting pool with {pool._processes} processes")

        try:
            for file_size, md5, _error in pool.imap(get_file_info, ({'path': file} for file in files), chunksize=100):
                print(file_size, md5)

        except KeyboardInterrupt:

            # Politely terminate workers
            pool.terminate()
            pool.join()

            return 1

    return 0
