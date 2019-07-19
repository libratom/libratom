# pylint: disable=broad-except,logging-fstring-interpolation,invalid-name,protected-access
"""
Set of utility functions that use spaCy to perform named entity recognition
"""

import logging
import multiprocessing
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import spacy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from libratom.models.entity import Base, Entity
from libratom.utils.concurrency import get_messages, libratom_job

logger = logging.getLogger(__name__)

OUTPUT_FILENAME_TEMPLATE = "{}_entities_{}.sqlite3"
SPACY_MODEL = "en_core_web_sm"  # Command line option?


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


@libratom_job
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


# def job(kwargs):
#     """
#     To get starmap behavior with imap, in a picklable function
#     """
#     return process_message(**kwargs)


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
    with multiprocessing.Pool(processes=jobs) as pool, open_db_session(
        Session
    ) as session:

        logger.info(f"Starting Pool with {pool._processes} processes")

        for ents, exc in pool.imap(
            process_message, get_messages(files, spacy_model=spacy_model), chunksize=100
        ):
            if exc:
                # report['Errors'] += 1
                logger.error(exc)

            for entity in ents:
                session.add(Entity(**entity))

            # report['Entities'] += len(entities)

            # Commit if we have 10k or more new entities
            if len(session.new) >= 10000:
                try:
                    session.commit()
                except:
                    session.rollback()
                    raise

    return 0
