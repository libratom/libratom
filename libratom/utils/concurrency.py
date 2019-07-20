# pylint: disable=logging-fstring-interpolation,broad-except,too-few-public-methods
"""
Set of utilities for parallel execution of libratom code
"""

import functools
import logging
import signal

from libratom.utils.pff import PffArchive

logger = logging.getLogger(__name__)


class MockProgress:
    """
    Default progress object in case none was supplied
    """

    def update(self, n_steps):
        """
        Do nothing
        """


def get_messages(files, **kwargs):
    """
    Message generator to feed a pool of processes from a directory of PST files
    """

    # Pop progress object from the optional arguments
    progress = kwargs.pop("progress", MockProgress())

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

                    except Exception as exc:
                        # Log and move on to the next message
                        logger.exception(exc)

            # Update progress (one unit per file)
            progress.update(1)

        except Exception as exc:
            # Log and move on to the next file
            logger.exception(exc)


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
