# pylint: disable=broad-except,logging-fstring-interpolation,invalid-name,protected-access
"""
Set of utility functions that use spaCy to perform named entity recognition
"""

import logging
import multiprocessing
from pathlib import Path
from typing import List

import spacy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from libratom.models.entity import Base, Entity
from libratom.utils.concurrency import get_messages, imap_job, worker_init
from libratom.utils.database import db_session

logger = logging.getLogger(__name__)

OUTPUT_FILENAME_TEMPLATE = "{}_entities_{}.sqlite3"
SPACY_MODEL = "en_core_web_sm"  # Command line option?
MESSAGE_BATCH_SIZE = 100
DB_COMMIT_BATCH_SIZE = 10000


@imap_job
def process_message(filename: str, message_id: int, message: str, spacy_model):
    """
    Job function for the worker processes
    """

    # Return basic types to avoid serialization issues

    try:
        # Extract entities from the message
        doc = spacy_model(message)

        entities = [
            {
                # Keys are column names from libratom.models.entity.Entity
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


def extract_entities(
    files: List[Path],
    destination: Path,
    jobs: int = None,
    log_level=logging.WARNING,
    **kwargs,
) -> int:
    """
    Main entity extraction function called by the CLI
    """

    logger.setLevel(log_level)

    # Load spacy model
    logger.info(f"Loading spacy model: {SPACY_MODEL}")
    spacy_model = spacy.load(SPACY_MODEL)

    # Make DB file's parents if needed
    destination.parent.mkdir(parents=True, exist_ok=True)

    # DB setup
    logger.info(f"Creating database file: {destination}")
    engine = create_engine(f"sqlite:///{destination}")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    # Start of multiprocessing
    with multiprocessing.Pool(
        processes=jobs, initializer=worker_init
    ) as pool, db_session(Session) as session:

        logger.info(f"Starting Pool with {pool._processes} processes")

        try:

            for ents, error in pool.imap(
                process_message,
                get_messages(files, spacy_model=spacy_model, **kwargs),
                chunksize=MESSAGE_BATCH_SIZE,
            ):
                if error:
                    logger.error(error)

                for entity in ents:
                    session.add(Entity(**entity))

                # Commit if we reach a certain amount of pending new entities
                if len(session.new) >= DB_COMMIT_BATCH_SIZE:
                    try:
                        session.commit()
                    except Exception as exc:
                        logger.exception(exc)
                        session.rollback()

        except KeyboardInterrupt:
            logger.warning("Cancelling running task")
            logger.info("Terminating workers")

            # Clean up process pool
            pool.terminate()
            pool.join()

            return 1

    return 0
