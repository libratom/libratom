# pylint: disable=logging-fstring-interpolation,invalid-name
"""
The functions in this module are entry points for ratom sub-commands, e.g. `ratom entities ...`
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import enlighten

from libratom.cli.utils import MockContext
from libratom.lib.core import get_set_of_files
from libratom.lib.database import db_init, db_session
from libratom.lib.entities import (
    OUTPUT_FILENAME_TEMPLATE,
    count_messages_in_files,
    extract_entities,
    load_spacy_model,
)
from libratom.lib.report import store_file_reports_in_db

logger = logging.getLogger(__name__)


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
            src.name, datetime.now().isoformat(timespec="seconds")
        )

    # DB setup
    Session = db_init(out)

    # Get set of PST files from the source
    files = get_set_of_files(src)

    if not files:
        logger.warning(f"No PST file found in {src}; nothing to do")
        return 0

    # Compute and store file information
    with progress_bar_context(
        total=len(files),
        desc="Retrieving file information",
        unit="files",
        color="green",
        leave=False,
    ) as file_bar, db_session(Session) as session:
        store_file_reports_in_db(files, session, progress_callback=file_bar.update)

    # Get the total number of messages
    with progress_bar_context(
        total=len(files),
        desc="Retrieving total message count",
        unit="files",
        color="green",
        leave=False,
    ) as file_bar:
        msg_count, files = count_messages_in_files(
            files, progress_callback=file_bar.update
        )

    # Get spaCy model
    logger.info(f"Loading spacy model: {spacy_model_name}")
    spacy_model = load_spacy_model(spacy_model_name)
    if not spacy_model:
        return 1

    # Make DB file's parents if needed
    out.parent.mkdir(parents=True, exist_ok=True)

    # Get messages and extract entities
    with progress_bar_context(
        total=msg_count, desc="Processing messages", unit="msg", color="green"
    ) as msg_bar, db_session(Session) as session:
        status = extract_entities(
            files=files,
            session=session,
            spacy_model=spacy_model,
            jobs=jobs,
            progress_callback=msg_bar.update,
        )

    logger.info("All done")

    return status
