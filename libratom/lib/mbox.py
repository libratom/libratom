# pylint: disable=attribute-defined-outside-init
"""
mbox parsing utilities
"""

import mailbox
from copy import deepcopy
from datetime import datetime
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Generator, List, Optional, Tuple, Union

from treelib import Tree

from libratom.lib.base import Archive, AttachmentMetadata
from libratom.lib.constants import BodyType
from libratom.lib.utils import guess_mime_type


class MboxArchive(Archive):
    """
    Wrapper class around mailbox.mbox for use in libratom code alongside other email formats.

    Attributes:
        tree: A tree representation of the folders/messages hierarchy
        filepath: The source file path
    """

    def __init__(self, file: Union[Path, str]):
        self.filepath = str(file)
        self._mailbox = mailbox.mbox(file)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._mailbox.close()

    def messages(self) -> Generator[Message, None, None]:
        """
        Generator function to iterate over the archive's messages
        """

        return (msg for msg in self._mailbox)

    @property
    def message_count(self) -> int:
        """
        Returns the total number of messages in the mailbox
        """

        return len(self._mailbox)

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
    def get_message_body(message: Message) -> Tuple[str, Optional[BodyType]]:
        """
        Returns the message body along with a plain body type
        """
        return MboxArchive.format_message(message), BodyType.PLAIN

    @staticmethod
    def get_message_headers(message: Message) -> str:
        """
        Returns the message headers as one multiline string
        """

        return "\n".join([f"{key}: {value}" for key, value in message.items()])

    def get_attachment_metadata(self, message: Message) -> List[AttachmentMetadata]:
        """
        Returns the metadata of all attachments in a given message
        """

        return [
            AttachmentMetadata(
                name=part.get_filename(),
                mime_type=part.get_content_type()
                or guess_mime_type(part.get_filename()),
                size=len(part.get_payload()),
            )
            for part in message.walk()
            if (content_disposition := part.get_content_disposition() or "").startswith(
                "attachment"
            )
            or content_disposition.startswith("inline")
        ]

    def _build_tree(self) -> None:
        """Builds the internal tree structure

        Builds the internal tree structure

        Returns:
            None
        """

        self._tree = Tree()

        # Set up root node
        self._tree.create_node("root", 0)

        # Set up children
        for i, message in enumerate(self.messages(), start=1):
            self._tree.create_node(
                f"Message index: {i}",
                i,
                parent=0,
                data=message,
            )

    @property
    def tree(self) -> Tree:
        """Returns the object's internal tree structure"""

        try:
            return self._tree
        except AttributeError:
            self._build_tree()
            return self._tree

    def get_message_by_id(self, message_id: int) -> Optional[Message]:
        """Gets a message by its index.
        If no message was found for the given index, None is returned.

        Args:
            message_id: The target message's index

        Returns:
            A Message object or None
        """

        try:
            return self.tree.get_node(message_id).data
        except AttributeError:
            return None

    @staticmethod
    def get_message_date(message: Message) -> datetime:
        return parsedate_to_datetime(message["Date"])
