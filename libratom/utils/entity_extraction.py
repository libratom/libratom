# pylint: disable=broad-except,logging-fstring-interpolation,invalid-name,protected-access
"""
Set of utility functions that use spaCy to perform named entity recognition
"""

import logging
import multiprocessing
import os
from collections import namedtuple
from importlib import reload
from pathlib import Path
from typing import List, Tuple

import pkg_resources
import spacy
from spacy.language import Language
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from libratom.models.entity import Base, Entity
from libratom.utils.concurrency import get_messages, imap_job, worker_init
from libratom.utils.database import db_session
from libratom.utils.pff import PffArchive

logger = logging.getLogger(__name__)

OUTPUT_FILENAME_TEMPLATE = "{}_entities_{}.sqlite3"

# Allow these to be set through the environment
MSG_BATCH_SIZE = int(os.environ.get("RATOM_MSG_BATCH_SIZE", 100))
DB_COMMIT_BATCH_SIZE = int(os.environ.get("RATOM_DB_COMMIT_BATCH_SIZE", 10000))

# Spacy trained model names
SPACY_MODEL_NAMES = [
    "de_core_news_sm",
    "es_core_news_sm",
    "es_core_news_md",
    "pt_core_news_sm",
    "it_core_news_sm",
    "nl_core_news_sm",
    "en_core_web_sm",
    "en_core_web_md",
    "en_core_web_lg",
    "fr_core_news_sm",
    "fr_core_news_md",
]

SPACY_MODELS = namedtuple("SpacyModels", SPACY_MODEL_NAMES)(*SPACY_MODEL_NAMES)


@imap_job
def process_message(
    filename: str, message_id: int, message: str, spacy_model: Language
) -> Tuple[List, str]:
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
        return [], str(exc)


def extract_entities(
    files: List[Path],
    destination: Path,
    spacy_model_name: str,
    jobs: int = None,
    **kwargs,
) -> int:
    """
    Main entity extraction function called by the CLI
    """

    # Load spacy model
    logger.info(f"Loading spacy model: {spacy_model_name}")

    try:
        spacy_model = spacy.load(spacy_model_name)

    except OSError as exc:
        logger.warning(f"Unable to load spacy model {spacy_model_name}")

        if "E050" in str(exc):
            # https://github.com/explosion/spaCy/blob/v2.1.6/spacy/errors.py#L207
            # Model not found, try installing it
            logger.warning(f"Downloading {spacy_model_name}")

            from spacy.cli.download import msg as spacy_msg

            # Download quietly
            spacy_msg.no_print = True
            try:
                spacy.cli.download(spacy_model_name, False, "--quiet")
            except SystemExit:
                logger.error(f"Unable to install spacy model {spacy_model_name}")
                logger.error("Exiting")

                return 1

            # Now try loading it again
            reload(pkg_resources)
            spacy_model = spacy.load(spacy_model_name)

        else:
            logger.exception(exc)
            return 1

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

        logger.info(f"Starting pool with {pool._processes} processes")

        try:

            for ents, error in pool.imap(
                process_message,
                get_messages(files, spacy_model=spacy_model, **kwargs),
                chunksize=MSG_BATCH_SIZE,
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
            logger.info(f"Partial results written to {destination}")
            logger.info("Terminating workers")

            # Clean up process pool
            pool.terminate()
            pool.join()

            return 1

    return 0


def get_msg_count(path: Path) -> int:
    """
    Get the number of messages for a given PST file path
    """

    try:
        with PffArchive(path) as pst_file:
            return pst_file.message_count

    except Exception as exc:
        logger.exception(exc)
        return 0
