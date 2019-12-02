# pylint: disable=consider-using-ternary,attribute-defined-outside-init
"""
PFF parsing utilities. Requires libpff.
"""

import logging
from collections import deque
from io import IOBase
from pathlib import Path
from typing import Generator, List, Optional, Union

import pypff
from treelib import Tree

from libratom.lib.base import Archive, AttachmentMetadata

logger = logging.getLogger(__name__)


class PffArchive(Archive):
    """Wrapper class around pypff.file

    Provides methods for manipulating a PFF archive

    Attributes:
        tree: A tree representation of the folders/messages hierarchy
    """

    def __init__(self, file: Union[Path, IOBase, str] = None) -> None:
        self.data = pypff.file()

        if file:
            self.load(file)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.data.close()

    def _build_tree(self) -> None:
        """Builds the internal tree structure

        Builds the internal tree structure

        Returns:
            None
        """

        self._tree = Tree()

        # Set up root node
        root = next(self.folders())
        self._tree.create_node("root", root.identifier)

        # Set up children
        for folder in self.folders():
            for message in folder.sub_messages:
                self._tree.create_node(
                    f"Message ID: {message.identifier}",
                    message.identifier,
                    parent=folder.identifier,
                    data=message,
                )

            for sub_folder in folder.sub_folders:
                self._tree.create_node(
                    sub_folder.name, sub_folder.identifier, parent=folder.identifier
                )

    def load(self, file: Union[Path, IOBase, str]) -> None:
        """Opens a PFF file using libpff

        Args:
            file: A path or file object

        Returns:
            None
        """

        if isinstance(file, IOBase):
            self.data.open_file_object(file)
        elif isinstance(file, (Path, str)):
            self.data.open(str(file), "rb")
        else:
            raise TypeError(f"Unable to load {file} of type {type(file)}")

    def folders(self, bfs: bool = True) -> Generator[pypff.folder, None, None]:
        """Generator function to iterate over the archive's folders

        Args:
            bfs: Whether the folder tree should be walked breadth first

        Yields:
            A pypff.folder object
        """

        folders = deque([self.data.root_folder])

        while folders:
            folder = folders.pop()

            yield folder

            if bfs:
                folders.extendleft(folder.sub_folders)
            else:
                folders.extend(folder.sub_folders)

    # fmt: off
    def messages(self, bfs: bool = True) -> Generator[pypff.message, None, None]:  # pylint: disable=arguments-differ
        """Generator function to iterate over the archive's messages

        Args:
            bfs: Whether the folder tree should be walked breadth first

        Yields:
            A pypff.message object
        """

        for folder in self.folders(bfs):
            for message in folder.sub_messages:
                yield message
    # fmt: on

    def get_message_by_id(self, message_id: int) -> Optional[pypff.message]:
        """Gets a message by its internal pff identifier.
        If no message was found for the given identifier, None is returned.

        Args:
            message_id: The target message's identifier attribute

        Returns:
            A pypff.message object or None
        """

        try:
            return self.tree.get_node(message_id).data
        except AttributeError:
            return None

    @property
    def tree(self) -> Tree:
        """Returns the object's internal tree structure
        """

        try:
            return self._tree
        except AttributeError:
            self._build_tree()
            return self._tree

    @property
    def message_count(self) -> int:
        """Returns the total number of messages in the archive

        Returns:
            An int
        """

        return sum(folder.number_of_sub_messages for folder in self.folders())

    @staticmethod
    def format_message(message: pypff.message, with_headers: bool = True) -> str:
        """Formats a pypff.message object into an RFC822 compliant string

        Args:
            message: A pypff.message object
            with_headers: whether to include the headers in the output

        Returns:
            A string
        """

        body = message.plain_text_body or message.html_body or message.rtf_body

        if not body:
            # Return headers only
            return message.transport_headers and message.transport_headers.strip() or ""

        if isinstance(body, bytes):
            body = str(body, encoding="utf-8", errors="replace")

        return f"{message.transport_headers if with_headers else ''}Body-Type: plain-text\r\n\r\n{body.strip()}"

    @staticmethod
    def get_attachment_metadata(message: pypff.message) -> List[AttachmentMetadata]:
        """
        Returns the metadata of all attachments in a given message
        """

        def get_mime_type(attachment):
            # pylint: disable=broad-except
            try:
                return (
                    attachment.record_sets[0]
                    .entries[14]
                    .data.decode("utf-16")
                    .rstrip("\0")
                )
            except Exception:
                return ""

        return [
            AttachmentMetadata(
                name=attachment.name,
                mime_type=get_mime_type(attachment),
                size=attachment.size,
            )
            for attachment in message.attachments
        ]
