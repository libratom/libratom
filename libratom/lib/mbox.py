"""
mbox parsing utilities
"""

import mailbox

from email.message import Message
from pathlib import Path
from typing import Union


class MboxArchive:
    """Wrapper class around mailbox.mbox for use in libratom code alongside other email formats.
    """

    def __init__(self, file: Union[Path, str]):
        self.mailbox = mailbox.mbox(file)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.mailbox.close()

    def messages(self):
        """
        """
        return self.mailbox.itervalues()

    @property
    def message_count(self) -> int:
        """
        Returns the total number of messages in the mailbox
        """

        return len(self.mailbox)

    @staticmethod
    def format_message(message: Message, with_headers: bool = True) -> str:
        """
        """
        return message.as_string()
