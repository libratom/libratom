# pylint: disable=broad-except,logging-fstring-interpolation,invalid-name,protected-access
"""
Set of utility functions that use spaCy to perform named entity recognition
"""

import logging
import multiprocessing
from datetime import datetime
from pathlib import Path

import spacy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from libratom.models.entity import Base, Entity
from libratom.utils.concurrency import get_messages, imap_job, worker_init
from libratom.utils.database import db_session

logger = logging.getLogger(__name__)

OUTPUT_FILENAME_TEMPLATE = "{}_entities_{}.sqlite3"
SPACY_MODEL = "en_core_web_sm"  # Command line option?


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
    source: Path, destination: Path, jobs: int = None, log_level=logging.WARNING
) -> int:
    """
    Main entity extraction function called by the CLI
    """

    logger.setLevel(log_level)

    # Resolve output file
    if destination.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        destination = destination / OUTPUT_FILENAME_TEMPLATE.format(
            source.name, datetime.now().isoformat(timespec="seconds")
        )
    else:
        # Make parent dirs if needed
        destination.parent.mkdir(parents=True, exist_ok=True)

    # Load spacy model
    logger.info(f"Loading spacy model: {SPACY_MODEL}")
    spacy_model = spacy.load(SPACY_MODEL)

    # DB setup
    logger.info(f"Creating database file: {destination}")
    engine = create_engine(f"sqlite:///{destination}")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    # Get list of files from the source
    if source.is_dir():
        files = list(source.glob("**/*.pst"))
    else:
        files = [source]

    # Start of multiprocessing
    with multiprocessing.Pool(
        processes=jobs, initializer=worker_init
    ) as pool, db_session(Session) as session:

        logger.info(f"Starting Pool with {pool._processes} processes")

        try:

            for ents, error in pool.imap(
                process_message,
                get_messages(files, spacy_model=spacy_model),
                chunksize=100,
            ):
                if error:
                    # report['Errors'] += 1
                    logger.error(error)

                for entity in ents:
                    session.add(Entity(**entity))

                # report['Entities'] += len(entities)

                # Commit if we have 10k or more new entities
                if len(session.new) >= 10000:
                    try:
                        session.commit()
                    except Exception as exc:
                        logger.exception(exc)
                        session.rollback()

        except KeyboardInterrupt:
            logger.warning('Cancelling running task')
            logger.info('Terminating workers')

            # Clean up process pool
            pool.terminate()
            pool.join()

            return 1

    return 0
