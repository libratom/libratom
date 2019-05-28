# pylint: disable=missing-docstring,logging-fstring-interpolation,invalid-name
import logging

import humanfriendly

from libratom.utils.pff import PffArchive

logger = logging.getLogger(__name__)


def test_extract_enron_messages(enron_dataset):
    nb_extracted = 0
    total_size = 0

    for pst_file in enron_dataset.glob("**/*.pst"):
        try:
            # Iterate over messages and copy message string
            with PffArchive(pst_file) as archive:
                for message in archive.messages():
                    _ = archive.format_message(message)

                    # Increment message count
                    nb_extracted += 1

            # Add file size to running total
            total_size += pst_file.stat().st_size

        except Exception as exc:  # pylint: disable=broad-except
            logger.info(f"Inspecting {pst_file}")
            logger.exception(exc)

    logger.info(
        f"Extracted {nb_extracted} messages from a total of {humanfriendly.format_size(total_size)}"
    )


def test_extract_enron_messages_from_file(enron_dataset_file):
    """Similar to test_extract_enron_messages but with parametrized fixture
    """
    try:
        # Iterate over messages and copy message string
        with PffArchive(enron_dataset_file) as archive:
            for message in archive.messages():
                _ = archive.format_message(message)

    except Exception as exc:  # pylint: disable=broad-except
        logger.info(f"Inspecting {enron_dataset_file}")
        logger.exception(exc)
