# pylint: disable=consider-using-ternary
"""
PFF parsing utilities. Requires libpff.
"""

import logging
from bisect import bisect_left
from collections import deque
from io import IOBase
from pathlib import Path
from typing import Generator, Union

import pypff
from treelib import Tree

logger = logging.getLogger(__name__)


class PffArchive:
    """Wrapper class around pypff.file

    Provides methods for manipulating a PFF archive

    Attributes:
        tree: A tree representation of the folders/messages hierarchy
    """

    def __init__(
        self, file: Union[Path, IOBase, str] = None, skip_tree: bool = False
    ) -> None:
        self._skip_tree = skip_tree
        self.data = pypff.file()
        self.tree = None

        if file:
            self.load(file)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.data.close()

    def _build_tree(self) -> None:
        """Builds the internal tree structure

        Builds the internal tree structure, unless self.skip_tree is truthy

        Returns:
            None
        """

        if self._skip_tree:
            logger.info("Skipping tree representation")
            return

        self.tree = Tree()

        # Set up root node
        root = next(self.folders())
        self.tree.create_node("root", root.identifier)

        # Set up children
        for folder in self.folders():
            for message in folder.sub_messages:
                self.tree.create_node(
                    f"Message ID: {message.identifier}",
                    message.identifier,
                    parent=folder.identifier,
                    data=message,
                )

            for sub_folder in folder.sub_folders:
                self.tree.create_node(
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

        self._build_tree()

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

    def messages(self, bfs=True) -> Generator[pypff.message, None, None]:
        """Generator function to iterate over the archive's messages

        Args:
            bfs: Whether the folder tree should be walked breadth first

        Yields:
            A pypff.message object
        """

        for folder in self.folders(bfs):
            for message in folder.sub_messages:
                yield message

    def get_message_by_id(self, message_id: int) -> pypff.message:
        """Gets a message by its ID

        Args:
            message_id: The target message's identifier attribute

        Returns:
            A pypff.message object
        """
        # fmt: off
        for folder in self.folders():
            messages = folder.sub_messages
            # Use the fact that message IDs are stored sequentially in a given folder
            if messages and messages[0].identifier <= message_id <= messages[-1].identifier:
                i = bisect_left([message.identifier for message in messages], message_id)
                if i != len(messages) and messages[i].identifier == message_id:
                    return messages[i]

        raise ValueError(f"No message found with identifier: {message_id}")
        # fmt: on

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
