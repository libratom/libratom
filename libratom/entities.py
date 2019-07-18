"""
Utility functions used for Named Entity Recognition tasks
"""

import logging

import spacy

logger = logging.getLogger(__name__)


def extract_entities(log_level):
    """
    Main entity extraction function called by the CLI
    """
    nlp = spacy.load("en_core_web_sm")

    assert nlp
    ### GET VERBOSE VALUE FROM CLI CTX

    logger.setLevel(log_level)

    #####

    logger.info('An info msg')
    logger.warning('A warning msg')
    logger.error('An error msg')

    # logging.error('something happened in entities')
