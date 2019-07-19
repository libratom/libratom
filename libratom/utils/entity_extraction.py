# pylint: disable=broad-except
"""
Set of utility functions that use spaCy to perform named entity recognition
"""

import logging
from contextlib import contextmanager

from libratom.utils.pff import PffArchive

logger = logging.getLogger(__name__)


@contextmanager
def open_db_session(session_factory):
    """
    Database session context manager
    """
    # pylint:disable=bare-except

    session = session_factory()

    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def get_messages(files, report):
    """
    Message generator to feed a pool of processes from a directory of PST files
    """

    # Iterate over files
    for pst_file in files:
        try:
            with PffArchive(pst_file) as archive:
                # Iterate over messages
                for message in archive.messages():
                    try:

                        yield {
                            # keyword arguments for process_message()
                            "filename": pst_file.name,
                            "message_id": message.identifier,
                            "message": archive.format_message(
                                message, with_headers=False
                            ),
                        }

                        # Update report per message
                        report["Messages"] += 1

                    except Exception as exc:
                        # Log and move on to the next message
                        logger.exception(exc)

            # Update report per file
            report["Files"] += 1
            report["Size"] += pst_file.stat().st_size

            # Update progress bar
            # progress.value += 1

        except Exception as exc:
            # Log and move on to the next file
            logger.exception(exc)


def job_function_factory(spacy_model):
    """
    Factory function that returns a worker function using a given spacy model
    """

    def process_message(filename: str, message_id: int, message: str):
        """
        Job function for the worker processes
        """

        # Return basic types to avoid serialization issues

        try:
            # Extract entities from the message
            doc = spacy_model(message)

            entities = [
                {
                    "text": ent.text,
                    "label_": ent.label_,
                    "filename": filename,
                    "message_id": message_id,
                }
                for ent in doc.ents
            ]

            return entities, None

        except Exception as exc:
            return None, str(exc)

    return lambda kwargs: process_message(**kwargs)
