# pylint: disable=logging-fstring-interpolation,invalid-name
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
from libratom.pff import PffArchive

logger = logging.getLogger(__name__)

OUTPUT_FILENAME_TEMPLATE = "{}_entities_{}.sqlite3"
SPACY_MODEL = "en_core_web_sm"



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
    # pylint:disable=broad-except

    # Iterate over files
    for pst_file in files:
        try:
            with PffArchive(pst_file) as archive:
                # Iterate over messages
                for message in archive.messages():
                    try:

                        yield {
                            # keyword arguments for process_message()
                            'filename': pst_file.name,
                            'message_id': message.identifier,
                            'message': archive.format_message(message, with_headers=False)
                        }

                        # Update report per message
                        report['Messages'] += 1

                    except Exception as exc:
                        # Log and move on to the next message
                        logger.exception(exc)

            # Update report per file
            report['Files'] += 1
            report['Size'] += pst_file.stat().st_size

            # Update progress bar
            # progress.value += 1

        except Exception as exc:
            # Log and move on to the next file
            logger.exception(exc)



def extract_entities(source: Path, destination: Path, jobs: int = None, log_level=logging.WARNING) -> None:
    """
    Main entity extraction function called by the CLI
    """

    logger.setLevel(log_level)

    # Resolve output file
    if destination.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        destination = destination / OUTPUT_FILENAME_TEMPLATE.format(source.name,
                                                                    datetime.now().isoformat(timespec='seconds'))
    else:
        # Make parent dirs if needed
        destination.parent.mkdir(parents=True, exist_ok=True)

    # Load spacy model
    logger.info(f'Loading spacy model: {SPACY_MODEL}')
    nlp = spacy.load(SPACY_MODEL)

    # DB setup
    logger.info(f'Creating database file: {destination}')
    engine = create_engine(f'sqlite:///{destination}')
    Session = sessionmaker(bind=engine)

    Base.metadata.create_all(engine)

    logger.info('An info msg')
    logger.warning('A warning msg')
    logger.error('An error msg')
    logger.info(f'jobs: {jobs}, out: {destination}')

    # logging.error('something happened in entities')


def process_message(filename: str, message_id: int, message: str):
    """
    Job function for the worker processes
    """

    # Return basic types to avoid serialization issues

    try:
        # Extract entities from the message
        doc = nlp(message)

        entities = [{'text': ent.text, 'label_': ent.label_, 'filename': filename, 'message_id': message_id} for ent in
                    doc.ents]

        return entities, None

    except Exception as exc:
        return None, str(exc)
