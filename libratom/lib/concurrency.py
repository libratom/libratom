# pylint: disable=broad-except,too-few-public-methods
"""
Set of utilities for parallel execution of libratom code
"""

import functools
import logging
import signal
from pathlib import Path
from typing import Callable, Dict, Generator, Iterable

from libratom.lib.core import RATOM_MSG_PROGRESS_STEP, open_mail_archive

logger = logging.getLogger(__name__)


def get_messages(
    files: Iterable[Path], progress_callback: Callable, with_content=True, **kwargs
) -> Generator[Dict, None, None]:
    """
    Message generator to feed a pool of processes from a directory of PST files
    """

    msg_count = 0

    # Iterate over files
    for file in files:
        try:
            with open_mail_archive(file) as archive:
                # Iterate over messages
                for message in archive.messages():
                    try:
                        # Keyword arguments for process_message()
                        res = {
                            "filepath": str(file),
                            "message_id": getattr(message, "identifier", None),
                            "attachments": archive.get_attachment_metadata(message),
                        }

                        if with_content:
                            res["message"] = archive.format_message(
                                message, with_headers=False
                            )

                        # Add any optional arguments
                        res.update(kwargs)

                        yield res

                    except Exception as exc:
                        # Log and move on to the next message
                        logger.info(f"Invalid message in file {file}")
                        logger.debug(exc, exc_info=True)

                    finally:
                        msg_count += 1

                        # Update progress every N messages
                        if not msg_count % RATOM_MSG_PROGRESS_STEP:
                            progress_callback(RATOM_MSG_PROGRESS_STEP)

        except Exception as exc:
            # Log and move on to the next file
            logger.info(f"Skipping file {file}")
            logger.debug(exc, exc_info=True)

    # Update progress with remaining message count
    progress_callback(msg_count % RATOM_MSG_PROGRESS_STEP)


def worker_init():
    """
    Initializer for worker processes that makes them ignore interrupt signals

    https://docs.python.org/3/library/signal.html#signal.signal
    https://docs.python.org/3/library/signal.html#signal.SIG_IGN
    """

    signal.signal(signal.SIGINT, signal.SIG_IGN)


def imap_job(func):
    """
    Decorator that lets us write imap job functions with unpacked keyword arguments
    """

    @functools.wraps(func)
    def wrapper(kwargs):
        return func(**kwargs)

    return wrapper
