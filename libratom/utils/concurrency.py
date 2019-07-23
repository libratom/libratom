# pylint: disable=logging-fstring-interpolation,broad-except,too-few-public-methods
"""
Set of utilities for parallel execution of libratom code
"""

import functools
import logging
import signal

from libratom.utils.pff import PffArchive

logger = logging.getLogger(__name__)

# Interval between progress updates in the message generator
MSG_PROGRESS_STEP = 10


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

    # Included in our message count per file, to track progress
    remainder = 0
    msg_count = 0

    # Iterate over files
    for pst_file in files:
        try:
            with PffArchive(pst_file) as archive:
                # Iterate over messages
                for msg_count, message in enumerate(
                    archive.messages(), start=1 + remainder
                ):
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

                        # Update progress every N messages
                        if not msg_count % MSG_PROGRESS_STEP:
                            progress.update(MSG_PROGRESS_STEP)

                    except Exception as exc:
                        # Log and move on to the next message
                        logger.exception(exc)

                # Number of messages not counted towards progress is carried over
                remainder = msg_count % MSG_PROGRESS_STEP

        except Exception as exc:
            # Log and move on to the next file
            logger.exception(exc)

    # Update progress with what's left
    progress.update(msg_count % MSG_PROGRESS_STEP)


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
