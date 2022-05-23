# pylint: disable=invalid-name,broad-except
"""
The functions in this module are entry points for ratom sub-commands, e.g. `ratom entities ...`
"""

import json
import logging
from datetime import datetime
from operator import itemgetter
from pathlib import Path
from typing import Optional

import enlighten
from packaging.version import parse
from sqlalchemy import func

from libratom.cli.utils import MockContext, install_spacy_model, list_spacy_models
from libratom.lib.core import (
    export_messages_from_file,
    get_set_of_files,
    get_spacy_models,
    load_spacy_model,
)
from libratom.lib.database import db_init, db_session
from libratom.lib.entities import extract_entities
from libratom.lib.report import generate_report, scan_files, store_configuration_in_db
from libratom.models import FileReport

logger = logging.getLogger(__name__)

OUTPUT_FILENAME_TEMPLATE = "{}_{}_{}.sqlite3"


def entities(
    out: Path,
    spacy_model_name: str,
    jobs: Optional[int],
    src: Path,
    include_message_contents: bool = False,
    progress: bool = False,
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

    # Try loading the spaCy model in case we need to download it first,
    # but don't cache it in the main process
    logger.info(f"Loading spaCy model: {spacy_model_name}")
    spacy_model = load_spacy_model(spacy_model_name)
    if not spacy_model:
        return 1

    # Try to see if we're using a stale model version
    spacy_model_version = spacy_model.meta.get("version")
    try:
        latest_version = get_spacy_models()[spacy_model_name][0]
        if parse(latest_version) > parse(spacy_model_version):
            logger.info(
                f"Model {spacy_model_name} {spacy_model_version} will be used, but {latest_version} is available"
            )
    except Exception as exc:
        logger.debug(exc, exc_info=True)

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
                spacy_model_name=spacy_model_name,
                include_message_contents=include_message_contents,
                jobs=jobs,
                processing_progress_callback=processing_msg_bar.update,
                reporting_progress_callback=reporting_msg_bar.update,
            )

    logger.info("All done")

    return status


def report(
    out: Path,
    jobs: Optional[int],
    src: Path,
    include_message_contents: bool = False,
    progress: bool = False,
) -> int:
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

    # Get messages and generate reports
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
                files=good_files,
                session=session,
                include_message_contents=include_message_contents,
                progress_callback=msg_bar.update,
            )

    logger.info("All done")

    return status


def model(_list: bool, install: str, upgrade: str, version: str) -> int:
    """
    Click sub command function called by `ratom model`
    """

    if install:
        return install_spacy_model(install, version, False)

    if upgrade:
        return install_spacy_model(upgrade, None, True)

    # List by default
    return list_spacy_models()


def emldump(out: Path, location: Path, src: Path) -> int:
    """
    Generate .eml files from pst/mbox files.
    """

    # Extract inputs from json file
    with src.open() as f:
        input_elements = json.load(f)

    # Process each file / id_list
    for input_element in input_elements:

        filename, id_list = itemgetter("filename", "id_list")(input_element)

        try:
            export_messages_from_file(location / filename, id_list, out)

        except Exception as exc:
            logger.warning(
                f"Skipping {location / filename}, reason: {exc}",
                exc_info=True,
            )

    return 0
