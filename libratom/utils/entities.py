import logging

import spacy


logger = logging.getLogger(__name__)


def extract_entities(verbose):
    # nlp = spacy.load("en_core_web_sm")

    ### GET VERBOSE VALUE FROM CLI CTX
    if verbose > 1:
        logger.setLevel(logging.DEBUG)
    elif verbose > 0:
        logger.setLevel(logging.INFO)

    #####

    logger.info('An info msg')
    logger.warning('A warning msg')
    logger.error('An error msg')

    # logging.error('something happened in entities')
