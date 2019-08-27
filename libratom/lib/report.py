# pylint: disable=broad-except
"""
Set of utility functions to generate job related reports
"""

import logging
import multiprocessing
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
    except Exception as exc:
        return None, str(exc)

    return size, None


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
            for file_size, _error in pool.imap(get_file_info, ({'path': file} for file in files), chunksize=100):
                print(file_size)

        except KeyboardInterrupt:

            # Politely terminate workers
            pool.terminate()
            pool.join()

            return 1

    return 0
