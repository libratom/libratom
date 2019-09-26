"""
mbox parsing utilities
"""

import mailbox
from email.message import Message
from pathlib import Path
from typing import Generator, Union

from libratom.lib.base import Archive


class MboxArchive(Archive):
    """Wrapper class around mailbox.mbox for use in libratom code alongside other email formats.
    """

    def __init__(self, file: Union[Path, str]):
        self.mailbox = mailbox.mbox(file)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.mailbox.close()

    def messages(self) -> Generator[Message, None, None]:
        """
        Generator function to iterate over the archive's messages
        """
        return self.mailbox.itervalues()  # noqa: B301

    @property
    def message_count(self) -> int:
        """
        Returns the total number of messages in the mailbox
        """

        return len(self.mailbox)

    @staticmethod
    def format_message(message: Message, with_headers: bool = True) -> str:
        """
        ...
        """
        return message.as_string()
