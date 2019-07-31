# pylint: disable=broad-except
"""
Database related utilities
"""
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def db_session(session_factory):
    """
    Database session context manager
    """

    session = session_factory()

    try:
        yield session
        if session.new or session.dirty or session.deleted:
            session.commit()

    except Exception as exc:
        logger.exception(exc)
        session.rollback()

    finally:
        session.close()
