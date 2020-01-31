# pylint: disable=broad-except,invalid-name,protected-access,consider-using-ternary,too-many-locals,too-many-arguments
"""
Set of utility functions that use spaCy to perform named entity recognition
"""

import logging
import multiprocessing
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from spacy.language import Language
from sqlalchemy.orm.session import Session

from libratom.lib.base import AttachmentMetadata
from libratom.lib.concurrency import get_messages, imap_job, worker_init
from libratom.lib.core import (
    RATOM_DB_COMMIT_BATCH_SIZE,
    RATOM_MSG_BATCH_SIZE,
    RATOM_MSG_PROGRESS_STEP,
)
from libratom.models import Attachment, Entity, FileReport, Message

logger = logging.getLogger(__name__)


@imap_job
def process_message(
    filepath: str,
    message_id: int,
    message: str,
    attachments: List[AttachmentMetadata],
    spacy_model: Language,
) -> Tuple[Dict, Optional[str]]:
    """
    Job function for the worker processes
    """

    # Return basic types to avoid serialization issues
    res = {
        "filepath": filepath,
        "message_id": message_id,
        "processing_start_time": datetime.utcnow(),
        "attachments": attachments,
    }

    try:
        # Extract entities from the message
        doc = spacy_model(message)
        res["entities"] = [(ent.text, ent.label_) for ent in doc.ents]

        res["processing_end_time"] = datetime.utcnow()

        return res, None

    except Exception as exc:
        return res, str(exc)


def extract_entities(
    files: Iterable[Path],
    session: Session,
    spacy_model: Language,
    jobs: int = None,
    processing_progress_callback: Callable = None,
    reporting_progress_callback: Callable = None,
    **kwargs,
) -> int:
    """
    Main entity extraction function that extracts named entities from a given iterable of files

    Spawns multiple processes via multiprocessing.Pool
    """

    # Confirm environment settings
    for key, value in globals().items():
        if key.startswith("RATOM_"):
            logger.debug(f"{key}: {value}")

    # Default progress callbacks to no-op
    processing_update_progress = processing_progress_callback or (lambda *_, **__: None)
    reporting_update_progress = reporting_progress_callback or (lambda *_, **__: None)

    # Load the file_report table for local lookup
    _file_reports = session.query(FileReport).all()  # noqa: F841

    # Start of multiprocessing
    with multiprocessing.Pool(processes=jobs, initializer=worker_init) as pool:

        logger.debug(f"Starting pool with {pool._processes} processes")

        new_entities = []
        msg_count = 0

        try:

            for msg_count, worker_output in enumerate(
                pool.imap_unordered(
                    process_message,
                    get_messages(
                        files,
                        spacy_model=spacy_model,
                        progress_callback=processing_update_progress,
                        **kwargs,
                    ),
                    chunksize=RATOM_MSG_BATCH_SIZE,
                ),
                start=1,
            ):

                # Unpack worker job output
                res, error = worker_output

                if error:
                    logger.info(
                        "Skipping message {message_id} from file {filepath}".format(
                            **res
                        )
                    )
                    logger.debug(
                        "File: {filepath}, message ID: {message_id}, {error}".format(
                            **res, error=error
                        )
                    )

                    continue

                # Extract results
                entities = res.pop("entities")
                message_id = res.pop("message_id")
                filepath = res.pop("filepath")
                attachments = res.pop("attachments")

                # Create new message instance
                message = Message(pff_identifier=message_id, **res)

                # Link message to a file_report
                try:
                    file_report = (
                        session.query(FileReport).filter_by(path=filepath).one()
                    )
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

                # Record entities info
                for entity in entities:
                    new_entities.append(
                        Entity(
                            text=entity[0],
                            label_=entity[1],
                            filepath=filepath,
                            message=message,
                            file_report=file_report,
                        )
                    )

                # Commit if we reach a certain amount of new entities
                if len(new_entities) >= RATOM_DB_COMMIT_BATCH_SIZE:
                    session.add_all(new_entities)
                    new_entities = []
                    try:
                        session.commit()
                    except Exception as exc:
                        logger.exception(exc)
                        session.rollback()

                # Update progress every N messages
                if not msg_count % RATOM_MSG_PROGRESS_STEP:
                    reporting_update_progress(RATOM_MSG_PROGRESS_STEP)

            # Add remaining new entities
            session.add_all(new_entities)

            # Update progress with remaining message count
            reporting_update_progress(msg_count % RATOM_MSG_PROGRESS_STEP)

        except KeyboardInterrupt:
            logger.warning("Cancelling running task")
            logger.info("Partial results written to database")
            logger.info("Terminating workers")

            # Clean up process pool
            pool.terminate()
            pool.join()

            return 1

    return 0
