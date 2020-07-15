# pylint: disable=missing-docstring

import os
from collections import namedtuple
from enum import Enum, auto

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
    "da_core_news_lg",
    "da_core_news_md",
    "da_core_news_sm",
    "de_core_news_lg",
    "de_core_news_md",
    "de_core_news_sm",
    "de_pytt_bertbasecased_lg",
    "de_trf_bertbasecased_lg",
    "el_core_news_lg",
    "el_core_news_md",
    "el_core_news_sm",
    "en_core_web_lg",
    "en_core_web_md",
    "en_core_web_sm",
    "en_depent_web_md",
    "en_pytt_bertbaseuncased_lg",
    "en_pytt_distilbertbaseuncased_lg",
    "en_pytt_robertabase_lg",
    "en_pytt_xlnetbasecased_lg",
    "en_trf_bertbaseuncased_lg",
    "en_trf_distilbertbaseuncased_lg",
    "en_trf_robertabase_lg",
    "en_trf_xlnetbasecased_lg",
    "en_vectors_glove_md",
    "en_vectors_web_lg",
    "es_core_news_lg",
    "es_core_news_md",
    "es_core_news_sm",
    "es_core_web_md",
    "fr_core_news_lg",
    "fr_core_news_md",
    "fr_core_news_sm",
    "fr_depvec_web_lg",
    "it_core_news_lg",
    "it_core_news_md",
    "it_core_news_sm",
    "ja_core_news_lg",
    "ja_core_news_md",
    "ja_core_news_sm",
    "lt_core_news_lg",
    "lt_core_news_md",
    "lt_core_news_sm",
    "nb_core_news_lg",
    "nb_core_news_md",
    "nb_core_news_sm",
    "nl_core_news_lg",
    "nl_core_news_md",
    "nl_core_news_sm",
    "pl_core_news_lg",
    "pl_core_news_md",
    "pl_core_news_sm",
    "pt_core_news_lg",
    "pt_core_news_md",
    "pt_core_news_sm",
    "ro_core_news_lg",
    "ro_core_news_md",
    "ro_core_news_sm",
    "xx_ent_wiki_sm",
    "zh_core_web_lg",
    "zh_core_web_md",
    "zh_core_web_sm",
]

SPACY_MODELS = namedtuple("SpacyModels", SPACY_MODEL_NAMES)(*SPACY_MODEL_NAMES)


class BodyType(Enum):
    PLAIN = auto()
    RTF = auto()
    HTML = auto()
