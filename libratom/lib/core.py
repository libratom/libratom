# pylint: disable=missing-docstring,broad-except,import-outside-toplevel,

import logging
import os
from collections import namedtuple
from importlib import reload
from pathlib import Path
from typing import List, Optional, Set, Tuple, Union

import pkg_resources
import spacy
from spacy.language import Language

from libratom.lib import MboxArchive, PffArchive
from libratom.lib.exceptions import FileTypeError

logger = logging.getLogger(__name__)


# Allow these to be set through the environment
RATOM_MSG_BATCH_SIZE = int(os.environ.get("RATOM_MSG_BATCH_SIZE", 1000))
RATOM_DB_COMMIT_BATCH_SIZE = int(os.environ.get("RATOM_DB_COMMIT_BATCH_SIZE", 3_000))

# Interval between progress updates in the message generator
RATOM_MSG_PROGRESS_STEP = int(os.environ.get("RATOM_MSG_PROGRESS_STEP", 10))

# Use the same default as spacy: https://github.com/explosion/spaCy/blob/v2.1.6/spacy/language.py#L130-L149
RATOM_SPACY_MODEL_MAX_LENGTH = int(
    os.environ.get("RATOM_SPACY_MODEL_MAX_LENGTH", 1_000_000)
)


# Spacy trained model names
SPACY_MODEL_NAMES = [
    "de_core_news_sm",
    "de_core_news_md",
    "el_core_news_sm",
    "el_core_news_md",
    "en_core_web_sm",
    "en_core_web_md",
    "en_core_web_lg",
    "es_core_news_sm",
    "es_core_news_md",
    "fr_core_news_sm",
    "fr_core_news_md",
    "it_core_news_sm",
    "lt_core_news_sm",
    "nb_core_news_sm",
    "nl_core_news_sm",
    "pt_core_news_sm",
    "xx_ent_wiki_sm",
]

SPACY_MODELS = namedtuple("SpacyModels", SPACY_MODEL_NAMES)(*SPACY_MODEL_NAMES)


def get_ratom_settings() -> List[Tuple[str, Union[int, str]]]:
    return [
        (key, value) for key, value in globals().items() if key.startswith("RATOM_")
    ]


def open_mail_archive(path: Path, **kwargs) -> Optional[Union[PffArchive, MboxArchive]]:

    extension_type_mapping = {".pst": PffArchive, ".mbox": MboxArchive}

    try:
        archive_class = extension_type_mapping[path.suffix]
    except KeyError:
        raise FileTypeError(f"Unable to open {path}. Unsupported file type.")

    return archive_class(path, **kwargs)


def get_set_of_files(path: Path) -> Set[Path]:
    if path.is_dir():
        return set(path.glob("**/*.pst")).union(set(path.glob("**/*.mbox")))

    return {path}


def load_spacy_model(spacy_model_name: str) -> Tuple[Optional[Language], Optional[int]]:
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
                return None, None

            # Now try loading it again
            reload(pkg_resources)
            spacy_model = spacy.load(spacy_model_name)

        else:
            logger.exception(exc)
            return None, None

    # Try to get spaCy model version
    try:
        spacy_model_version = pkg_resources.get_distribution(spacy_model_name).version
    except Exception as exc:
        spacy_model_version = None
        logger.info(
            f"Unable to get spaCy model version for {spacy_model_name}, error: {exc}"
        )

    # Set text length limit for model
    spacy_model.max_length = RATOM_SPACY_MODEL_MAX_LENGTH

    return spacy_model, spacy_model_version
