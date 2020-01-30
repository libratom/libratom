# pylint: disable=invalid-name
"""
The functions in this module are entry points for ratom sub-commands, e.g. `ratom entities ...`
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import enlighten
from sqlalchemy import func

from libratom.cli.utils import MockContext
from libratom.lib.core import get_set_of_files, load_spacy_model
from libratom.lib.database import db_init, db_session
from libratom.lib.entities import extract_entities
from libratom.lib.report import generate_report, scan_files, store_configuration_in_db
from libratom.models import FileReport

logger = logging.getLogger(__name__)

OUTPUT_FILENAME_TEMPLATE = "{}_{}_{}.sqlite3"


def entities(
    out: Path, spacy_model_name: str, jobs: Optional[int], src: Path, progress: bool
) -> int:
    """
    Click sub command function called by `ratom entities`
    """

    # Make or fake our progress bar context objects
    if progress:
        progress_bars = enlighten.get_manager()
        progress_bar_context = progress_bars.counter
    else:
        progress_bar_context = MockContext

    # Resolve output file based on src parameter
    if out.is_dir():
        out = out / OUTPUT_FILENAME_TEMPLATE.format(
            src.name,
            "entities",
            datetime.now()
            .isoformat(timespec="seconds")
            .translate(str.maketrans({"-": "", ":": ""})),
        )

    # Make DB file's parents if needed
    out.parent.mkdir(parents=True, exist_ok=True)

    # DB setup
    Session = db_init(out)

    # Get set of PST files from the source
    files = get_set_of_files(src)

    if not files:
        logger.info(f"No PST file found in {src}")

    # Compute and store file information
    with progress_bar_context(
        total=len(files),
        desc="Initial file scan",
        unit="files",
        color="green",
        leave=False,
    ) as file_bar, db_session(Session) as session:
        status = scan_files(
            files, session, jobs=jobs, progress_callback=file_bar.update
        )

    if status == 1:
        logger.warning("Aborting")
        return status

    # Get spaCy model
    logger.info(f"Loading spacy model: {spacy_model_name}")
    spacy_model, spacy_model_version = load_spacy_model(spacy_model_name)
    if not spacy_model:
        return 1

    # Get messages and extract entities
    with db_session(Session) as session:

        # Record configuration info
        store_configuration_in_db(
            session, str(src), jobs, spacy_model_name, spacy_model_version
        )

        # Get total message count
        msg_count = session.query(func.sum(FileReport.msg_count)).scalar()

        # Get list of good files
        good_files = [
            Path(file.path)
            for file in session.query(FileReport).filter(FileReport.error.is_(None))
        ]

        with progress_bar_context(
            total=msg_count, desc="Processing messages", unit="msg", color="blue"
        ) as processing_msg_bar, progress_bar_context(
            total=msg_count,
            desc="Generating message reports",
            unit="msg",
            color="green",
        ) as reporting_msg_bar:

            status = extract_entities(
                files=good_files,
                session=session,
                spacy_model=spacy_model,
                jobs=jobs,
                processing_progress_callback=processing_msg_bar.update,
                reporting_progress_callback=reporting_msg_bar.update,
            )

    logger.info("All done")

    return status


def report(out: Path, jobs: Optional[int], src: Path, progress: bool) -> int:
    """
    Click sub command function called by `ratom report`
    """

    # Make or fake our progress bar context objects
    if progress:
        progress_bars = enlighten.get_manager()
        progress_bar_context = progress_bars.counter
    else:
        progress_bar_context = MockContext

    # Resolve output file based on src parameter
    if out.is_dir():
        out = out / OUTPUT_FILENAME_TEMPLATE.format(
            src.name,
            "report",
            datetime.now()
            .isoformat(timespec="seconds")
            .translate(str.maketrans({"-": "", ":": ""})),
        )

    # Make DB file's parents if needed
    out.parent.mkdir(parents=True, exist_ok=True)

    # DB setup
    Session = db_init(out)

    # Get set of PST files from the source
    files = get_set_of_files(src)

    if not files:
        logger.info(f"No PST file found in {src}")

    # Compute and store file information
    with progress_bar_context(
        total=len(files),
        desc="Initial file scan",
        unit="files",
        color="green",
        leave=False,
    ) as file_bar, db_session(Session) as session:
        status = scan_files(
            files, session, jobs=jobs, progress_callback=file_bar.update
        )

    if status == 1:
        logger.warning("Aborting")
        return status

    # Get messages and extract entities
    with db_session(Session) as session:

        # Record configuration info
        store_configuration_in_db(session, str(src), jobs)

        # Get total message count
        msg_count = session.query(func.sum(FileReport.msg_count)).scalar()

        # Get list of good files
        good_files = [
            Path(file.path)
            for file in session.query(FileReport).filter(FileReport.error.is_(None))
        ]

        with progress_bar_context(
            total=msg_count, desc="Processing messages", unit="msg", color="green"
        ) as msg_bar:

            status = generate_report(
                files=good_files, session=session, progress_callback=msg_bar.update,
            )

    logger.info("All done")

    return status
