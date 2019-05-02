import logging

logger = logging.getLogger(__name__)

try:
    import pypff
except ImportError:
    logger.exception(
        f"No pypff support found. {__name__} requires libpff and its python bindings"
    )
    raise
