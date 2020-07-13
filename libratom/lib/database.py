# pylint: disable=broad-except
"""
Database related utilities
"""
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import ContextManager

from click.testing import Result
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

logger = logging.getLogger(__name__)

Base = declarative_base()


def db_init(db_file: Path) -> sessionmaker:
    """
    Initializes the database and returns a session factory
    """

    logger.info(f"Creating database file: {db_file}")
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)

    return sessionmaker(bind=engine)


@contextmanager
def db_session(session_factory: sessionmaker) -> ContextManager[Session]:
    """
    Database session context manager
    """

    session = session_factory()

    try:
        yield session
        if session.new or session.dirty or session.deleted:
            session.commit()

    except SQLAlchemyError as exc:
        logger.exception(exc)
        session.rollback()

    finally:
        session.close()


def db_session_from_cmd_out(result: Result) -> ContextManager[Session]:
    """
    Convenience function to inspect the DB output of a ratom command
    """

    # Find DB file in command result
    db_file = None
    for line in result.output.splitlines():
        if line.startswith("Creating database file:"):
            db_file = Path(line.rsplit(maxsplit=1)[1].strip())

    # Sanity check
    if not (db_file and db_file.is_file()):
        raise ValueError(f"Invalid database file: {db_file}")

    # Return session factory
    engine = create_engine(f"sqlite:///{db_file}")
    return db_session(sessionmaker(bind=engine))
