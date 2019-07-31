# pylint: disable=broad-except,logging-fstring-interpolation,invalid-name,protected-access,consider-using-ternary
"""
Set of utility functions that use spaCy to perform named entity recognition
"""

import logging
import multiprocessing
import os
from collections import namedtuple
from importlib import reload
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Set, Tuple

import pkg_resources
import spacy
from spacy.language import Language
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from libratom.lib.concurrency import get_messages, imap_job, worker_init
from libratom.lib.database import db_session
from libratom.lib.pff import PffArchive
from libratom.models.entity import Base, Entity

logger = logging.getLogger(__name__)

OUTPUT_FILENAME_TEMPLATE = "{}_entities_{}.sqlite3"

# Allow these to be set through the environment
RATOM_MSG_BATCH_SIZE = int(os.environ.get("RATOM_MSG_BATCH_SIZE", 100))
RATOM_DB_COMMIT_BATCH_SIZE = int(os.environ.get("RATOM_DB_COMMIT_BATCH_SIZE", 10_000))

# Use the same default as spacy: https://github.com/explosion/spaCy/blob/v2.1.6/spacy/language.py#L130-L149
RATOM_SPACY_MODEL_MAX_LENGTH = int(
    os.environ.get("RATOM_SPACY_MODEL_MAX_LENGTH", 1_000_000)
)

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
) -> Tuple[List, str, int, Optional[str]]:
    """
    Job function for the worker processes
    """

    # Return basic types to avoid serialization issues

    try:
        # Extract entities from the message
        doc = spacy_model(message)
        entities = [(ent.text, ent.label_) for ent in doc.ents]

        return entities, filename, message_id, None

    except Exception as exc:
        return [], filename, message_id, str(exc)


def load_spacy_model(spacy_model_name: str) -> Optional[Language]:
    """
    Loads and returns a given spaCy model

    If the model is not present, an attempt will be made to download and install it
    """

    try:
        spacy_model = spacy.load(spacy_model_name)

    except OSError as exc:
        logger.info(f"Unable to load spacy model {spacy_model_name}")

        if "E050" in str(exc):
            # https://github.com/explosion/spaCy/blob/v2.1.6/spacy/errors.py#L207
            # Model not found, try installing it
            logger.info(f"Downloading {spacy_model_name}")

            from spacy.cli.download import msg as spacy_msg

            # Download quietly
            spacy_msg.no_print = True
            try:
                spacy.cli.download(spacy_model_name, False, "--quiet")
            except SystemExit:
                logger.error(f"Unable to install spacy model {spacy_model_name}")
                return None

            # Now try loading it again
            reload(pkg_resources)
            spacy_model = spacy.load(spacy_model_name)

        else:
            logger.exception(exc)
            return None

    # Set text length limit for model
    spacy_model.max_length = RATOM_SPACY_MODEL_MAX_LENGTH

    return spacy_model


def extract_entities(
    files: Iterable[Path],
    destination: Path,
    spacy_model: Language,
    jobs: int = None,
    **kwargs,
) -> int:
    """
    Main entity extraction function that extracts named entities from a given iterable of files

    Spawns multiples processes via multiprocessing.Pool
    """

    # Confirm environment settings
    for key, value in globals().items():
        if key.startswith("RATOM_"):
            logger.debug(f"{key}: {value}")

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

            for ents, filename, message_id, error in pool.imap(
                process_message,
                get_messages(files, spacy_model=spacy_model, **kwargs),
                chunksize=RATOM_MSG_BATCH_SIZE,
            ):
                if error:
                    logger.warning(
                        f"Skipping message {message_id} from file {filename}"
                    )
                    logger.debug(f"File: {filename}, message ID: {message_id}, {error}")

                for entity in ents:
                    session.add(
                        Entity(
                            text=entity[0],
                            label_=entity[1],
                            filename=filename,
                            message_id=message_id,
                        )
                    )

                # Commit if we reach a certain amount of pending new entities
                if len(session.new) >= RATOM_DB_COMMIT_BATCH_SIZE:
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


def count_messages_in_files(
    files: Iterable[Path], progress_callback: Callable = None
) -> Tuple[int, Set[Path]]:
    """
    Get the number of messages in a set of PST files

    Return the total message count and a set of the valid files

    Used by the main entity extraction function to perform an initial scan
    """

    # Default progress callback to no-op
    update_progress = progress_callback or (lambda *_, **__: None)

    msg_count, good_files = 0, set()

    for file in files:
        try:
            with PffArchive(file) as pst_file:
                msg_count += pst_file.message_count

            good_files.add(file)

        except Exception as exc:
            logger.warning(f"Skipping file {file.name}")
            logger.debug(exc, exc_info=True)

        update_progress()

    return msg_count, good_files
