"""
Extension of the Archive class to support .eml files (single message archive)
"""

import email
import locale
from pathlib import Path
from typing import Union

from libratom.lib.mbox import MboxArchive


class EmlArchive(MboxArchive):
    """
    Code reuse hack
    """

    def __init__(self, file: Union[Path, str]):  # pylint: disable=super-init-not-called
        self.filepath = str(file)
        self._mailbox = set()

        with open(self.filepath, "r", encoding=locale.getpreferredencoding()) as f:
            self._mailbox.add(email.message_from_file(f, policy=email.policy.default))

    def __exit__(self, *_):
        pass
