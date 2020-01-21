# pylint: disable=broad-except,protected-access
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

import libratom
from libratom.lib.concurrency import get_messages, imap_job, worker_init
from libratom.lib.core import open_mail_archive
from libratom.models import Attachment, Configuration, FileReport, Message

logger = logging.getLogger(__name__)

# Interval between progress updates in the message generator
MSG_PROGRESS_STEP = int(os.environ.get("RATOM_MSG_PROGRESS_STEP", 10))


@imap_job
def get_file_info(path: Path) -> Tuple[Dict, Optional[str]]:
    """
    For a given file path, returns the size, md5 and sha256 checksums
    """

    path_str, name = str(path), path.name
    res = {"path": path_str, "name": name}

    try:
        size = os.stat(path_str).st_size

        md5 = hashlib.md5()
        sha256 = hashlib.sha256()

        # First we read the file one block at a time and update digests
        with open(path_str, "rb") as f:
            for block in iter(partial(f.read, 128), b""):
                md5.update(block)
                sha256.update(block)

        md5, sha256 = md5.hexdigest(), sha256.hexdigest()

        res.update({"size": size, "md5": md5, "sha256": sha256})

        # Then we try to get a message count
        try:
            with open_mail_archive(path) as archive:
                res["msg_count"] = archive.message_count

        except Exception as exc:
            res["error"] = str(exc)

    except Exception as exc:
        return res, str(exc)

    return res, None


def scan_files(
    files: Iterable[Path],
    session: Session,
    jobs: Optional[int] = None,
    progress_callback: Callable = None,
) -> int:
    """
    Extracts information from a list of email files and stores it in a database via an ORM session object
    """

    # Default progress callback to no-op
    update_progress = progress_callback or (lambda *_, **__: None)

    with multiprocessing.Pool(processes=jobs, initializer=worker_init) as pool:

        logger.debug(f"Starting pool with {pool._processes} processes")

        try:
            for values, exc in pool.imap(
                get_file_info, ({"path": file} for file in files), chunksize=1
            ):
                if not exc:
                    # Make a new FileReport object with the results
                    session.add(FileReport(**values))
                else:
                    logger.info(
                        f"Unable to retrieve file information for {values['path']}, error: {exc}"
                    )

                update_progress()

        except KeyboardInterrupt:
            logger.warning("Aborting")

            # Politely terminate workers
            pool.terminate()
            pool.join()

            return 1

    return 0


def store_configuration_in_db(
    session: Session,
    spacy_model: Optional[str] = None,
    spacy_model_version: Optional[int] = None,
) -> None:
    """
    Store configuration / environment information in the database output during a ratom command execution
    """

    configuration = {
        "cpu_count": multiprocessing.cpu_count(),
        "libratom_version": libratom.__version__,
        "spacy_model_name": spacy_model,
        "spacy_model_version": spacy_model_version,
    }

    session.add_all(
        [
            Configuration(name=name, value=str(value))
            for name, value in configuration.items()
        ]
    )


def generate_report(
    files: Iterable[Path],
    session: Session,
    progress_callback: Optional[Callable] = None,
) -> int:
    """
    Store full archive report in the DB
    """

    # Confirm environment settings
    for key, value in globals().items():
        if key.startswith("RATOM_"):
            logger.debug(f"{key}: {value}")

    # Default progress callback to no-op
    update_progress = progress_callback or (lambda *_, **__: None)

    # Load the file_report table for local lookup
    _file_reports = session.query(FileReport).all()  # noqa: F841

    msg_count = 0

    try:

        for msg_count, msg_info in enumerate(
            get_messages(files, with_content=False), start=1
        ):

            # Extract results
            message_id = msg_info.pop("message_id")
            filepath = msg_info.pop("filepath")
            attachments = msg_info.pop("attachments")

            # Create new message instance
            message = Message(pff_identifier=message_id, **msg_info)

            # Link message to a file_report
            try:
                file_report = session.query(FileReport).filter_by(path=filepath).one()
            except Exception as exc:
                file_report = None
                logger.info(
                    f"Unable to link message id {message_id} to a file. Error: {exc}"
                )

            message.file_report = file_report
            session.add(message)

            # Record attachment info
            session.add_all(
                [
                    Attachment(
                        **attachment._asdict(),
                        message=message,
                        file_report=file_report,
                    )
                    for attachment in attachments
                ]
            )

            # Update progress every N messages
            if not msg_count % MSG_PROGRESS_STEP:
                update_progress(MSG_PROGRESS_STEP)

        # Update progress with remaining message count
        update_progress(msg_count % MSG_PROGRESS_STEP)

    except KeyboardInterrupt:
        logger.warning("Cancelling running task")
        logger.info("Partial results written to database")

        return 1

    return 0
