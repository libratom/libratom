# pylint: disable=broad-except,logging-fstring-interpolation,protected-access
"""
Set of utility functions to generate job related reports
"""

import hashlib
import logging
import multiprocessing
import os
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Tuple

from sqlalchemy.orm.session import Session

from libratom.lib.concurrency import imap_job, worker_init
from libratom.models.file_report import FileReport

logger = logging.getLogger(__name__)


@imap_job
def get_file_info(path: Path) -> Tuple[Dict, Optional[str]]:
    """
    For a given file path, returns the size, md5 and sha256 checksums
    """

    path, name = str(path), path.name
    res = {"path": path, "name": name}

    try:
        size = os.stat(path).st_size

        md5 = hashlib.md5()
        sha256 = hashlib.sha256()

        # Read file one block at a time and update digests
        with open(path, "rb") as f:
            for block in iter(partial(f.read, 128), b""):
                md5.update(block)
                sha256.update(block)

        md5, sha256 = md5.hexdigest(), sha256.hexdigest()

        res.update({"size": size, "md5": md5, "sha256": sha256})

    except Exception as exc:
        return res, str(exc)

    return res, None


def store_file_reports_in_db(
    files: Iterable[Path],
    session: Session,
    jobs=None,
    progress_callback: Callable = None,
) -> int:
    """
    Computes checksums from a list of files and record them in a database via an ORM session object
    """

    # Default progress callback to no-op
    update_progress = progress_callback or (lambda *_, **__: None)

    with multiprocessing.Pool(processes=jobs, initializer=worker_init) as pool:

        print(f"Starting pool with {pool._processes} processes")

        try:
            for values, error in pool.imap(
                get_file_info, ({"path": file} for file in files), chunksize=100
            ):
                if not error:
                    session.add(FileReport(**values))
                else:
                    logger.warning(
                        f"Unable to retrieve file information for {values['path']}, error: {error}"
                    )

                update_progress()

        except KeyboardInterrupt:

            # Politely terminate workers
            pool.terminate()
            pool.join()

            return 1

    return 0
