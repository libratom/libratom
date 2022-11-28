# pylint: disable=broad-except,protected-access
"""
Set of utility functions to generate job related reports
"""

import hashlib
import logging
import multiprocessing
import os
from dataclasses import asdict
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Tuple

from sqlalchemy.orm.session import Session

import libratom
from libratom.lib.concurrency import get_messages, imap_job, worker_init
from libratom.lib.core import get_ratom_settings, open_mail_archive
from libratom.lib.headers import (
    get_header_field_type_mapping,
    populate_header_field_types,
)
from libratom.lib.utils import cleanup_message_body
from libratom.models import Attachment, Configuration, FileReport, HeaderField, Message

logger = logging.getLogger(__name__)


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
    src: str,
    jobs: int,
    spacy_model: Optional[str] = None,
    spacy_model_version: Optional[int] = None,
) -> None:
    """
    Store configuration / environment information in the database output during a ratom command execution
    """

    configuration = {
        "source": src,
        "jobs": jobs,
        "libratom_version": libratom.__version__,
        "spacy_model_name": spacy_model,
        "spacy_model_version": spacy_model_version,
    }

    settings = [
        Configuration(name=key, value=str(value))
        for key, value in configuration.items()
    ]

    settings.extend(
        [
            Configuration(name=key, value=str(value))
            for key, value in get_ratom_settings()
        ]
    )

    session.add_all(settings)
    session.commit()


def generate_report(
    files: Iterable[Path],
    session: Session,
    include_message_contents: bool = False,
    progress_callback: Optional[Callable] = None,
) -> int:
    """
    Store full archive report in the DB
    """

    # Confirm environment settings
    for key, value in get_ratom_settings():
        logger.debug(f"{key}: {value}")

    # Default progress callback to no-op
    update_progress = progress_callback or (lambda *_, **__: None)

    # Load the file_report table for local lookup
    _file_reports = session.query(FileReport).all()  # noqa: F841

    # Add header field type table
    if include_message_contents:
        populate_header_field_types(session)

    # Cache header field types into local mapping,
    # empty if header field type table was not created
    header_field_type_mapping = get_header_field_type_mapping(session)

    try:

        for msg_info in get_messages(
            files,
            progress_callback=update_progress,
            with_content=include_message_contents,
            with_headers=include_message_contents,
        ):

            # Extract results
            message_id = msg_info.pop("message_id")
            filepath = msg_info.pop("filepath")
            attachments = msg_info.pop("attachments")

            if include_message_contents:
                msg_info["body"] = cleanup_message_body(
                    msg_info["body"], msg_info.pop("body_type")
                )

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
                        **asdict(attachment),
                        message=message,
                        file_report=file_report,
                    )
                    for attachment in attachments
                ]
            )

            # Record header fields
            if include_message_contents:
                header_fields = []

                for line in (msg_info.get("headers") or "").splitlines():
                    try:
                        header_name, header_value = line.split(":", maxsplit=1)
                    except ValueError:
                        continue
                    if header_field_type := header_field_type_mapping.get(
                        header_name.lower()
                    ):
                        header_fields.append(
                            HeaderField(
                                header_field_type=header_field_type,
                                value=header_value,
                                message=message,
                            )
                        )

                session.add_all(header_fields)

    except KeyboardInterrupt:
        logger.warning("Cancelling running task")
        logger.info("Partial results written to database")

        return 1

    return 0
