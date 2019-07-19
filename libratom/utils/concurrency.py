# pylint: disable=logging-fstring-interpolation,broad-except
"""
Set of utilities for parallel execution of libratom code
"""

import functools
import logging

from libratom.utils.pff import PffArchive

logger = logging.getLogger(__name__)


def get_messages(files, **kwargs):
    """
    Message generator to feed a pool of processes from a directory of PST files
    """

    # Iterate over files
    for pst_file in files:

        logger.info(f"Processing {pst_file}")

        try:
            with PffArchive(pst_file) as archive:
                # Iterate over messages
                for message in archive.messages():
                    try:
                        # Keyword arguments for process_message()
                        res = {
                            "filename": pst_file.name,
                            "message_id": message.identifier,
                            "message": archive.format_message(
                                message, with_headers=False
                            ),
                        }

                        # Add any optional arguments
                        res.update(kwargs)

                        yield res

                        # Update report per message
                        # report["Messages"] += 1

                    except Exception as exc:
                        # Log and move on to the next message
                        logger.exception(exc)

            # Update report per file
            # report["Files"] += 1
            # report["Size"] += pst_file.stat().st_size

            # Update progress bar
            # progress.value += 1

        except Exception as exc:
            # Log and move on to the next file
            logger.exception(exc)


def libratom_job(func):
    """
    Decorator that lets us write imap job functions with unpacked keyword arguments
    """

    @functools.wraps(func)
    def wrapper(kwargs):
        return func(**kwargs)

    return wrapper
