# pylint: disable=logging-fstring-interpolation,invalid-name
"""
Utility functions used for Named Entity Recognition tasks
"""

import logging
from datetime import datetime
from pathlib import Path

import multiprocessing

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import spacy

from libratom.models.entity import Entity, Base

logger = logging.getLogger(__name__)

OUTPUT_FILENAME_TEMPLATE = "{}_entities_{}.sqlite3"
SPACY_MODEL = "en_core_web_sm"


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
