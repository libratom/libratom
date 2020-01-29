# pylint: disable=missing-docstring,broad-except

import os
from collections import namedtuple
from pathlib import Path
from typing import Optional, Set, Union

from libratom.lib import MboxArchive, PffArchive
from libratom.lib.exceptions import FileTypeError

# Allow these to be set through the environment
RATOM_MSG_BATCH_SIZE = int(os.environ.get("RATOM_MSG_BATCH_SIZE", 1000))
RATOM_DB_COMMIT_BATCH_SIZE = int(os.environ.get("RATOM_DB_COMMIT_BATCH_SIZE", 3_000))

# Interval between progress updates in the message generator
MSG_PROGRESS_STEP = int(os.environ.get("RATOM_MSG_PROGRESS_STEP", 10))

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
