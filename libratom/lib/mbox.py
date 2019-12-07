"""
mbox parsing utilities
"""

import mailbox
from copy import deepcopy
from email.message import Message
from pathlib import Path
from typing import Generator, List, Union

from libratom.lib.base import Archive, AttachmentMetadata


class MboxArchive(Archive):
    """
    Wrapper class around mailbox.mbox for use in libratom code alongside other email formats.
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
        Returns an RFC822 compliant string with or without headers
        """

        if with_headers:
            pass  # placeholder

        for part in message.walk():
            content_type = part.get_content_type()
            if content_type in {"text/plain", "message/rfc822"}:

                # https://bugs.python.org/issue27321
                # https://www.w3.org/Protocols/rfc1341/5_Content-Transfer-Encoding.html
                if "content-transfer-encoding" not in part:
                    part = deepcopy(part)
                    part["content-transfer-encoding"] = "8bit"

                return part.as_string()

        return ""

    @staticmethod
    def get_attachment_metadata(message: Message) -> List[AttachmentMetadata]:
        """
        Returns the metadata of all attachments in a given message
        """

        return [
            AttachmentMetadata(
                name=part.get_filename(),
                mime_type=part.get_content_type(),
                size=len(part.get_payload()),
            )
            for part in message.walk()
            if part.get_content_disposition() == "attachment"
        ]
