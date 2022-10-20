# pylint: disable=consider-using-ternary,attribute-defined-outside-init
"""
PFF parsing utilities. Requires libpff.
"""

import logging
from collections import defaultdict, deque
from datetime import datetime
from io import IOBase
from pathlib import Path
from typing import Generator, List, Optional, Tuple, Union

import pypff
from treelib import Tree

from libratom.data import MIME_TYPE_REGISTRIES
from libratom.lib.base import Archive, AttachmentMetadata
from libratom.lib.constants import BodyType
from libratom.lib.utils import decode, guess_mime_type

logger = logging.getLogger(__name__)


class PffArchive(Archive):
    """Wrapper class around pypff.file

    Provides methods for manipulating a PFF archive

    Attributes:
        tree: A tree representation of the folders/messages hierarchy
        filepath: The source file path
    """

    def __init__(self, file: Union[Path, IOBase, str] = None) -> None:
        self.filepath = None
        self._data = pypff.file()
        self._encodings = ["utf-8", "utf-16"]
        self._mime_indices = defaultdict(int)

        if file:
            self.load(file)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._data.close()

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
            self._data.open_file_object(file)
        elif isinstance(file, (Path, str)):
            self._data.open(str(file), "rb")
        else:
            raise TypeError(f"Unable to load {file} of type {type(file)}")

        self.filepath = str(file)

    def folders(self, bfs: bool = True) -> Generator[pypff.folder, None, None]:
        """Generator function to iterate over the archive's folders

        Args:
            bfs: Whether the folder tree should be walked breadth first

        Yields:
            A pypff.folder object
        """

        folders = deque([self._data.root_folder])

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
            try:
                for message in folder.sub_messages:
                    yield message
            except OSError as exc:
                logger.debug(exc, exc_info=True)
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
        """Returns the object's internal tree structure"""

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

        def safe_count(folder: pypff.folder) -> int:
            try:
                return folder.number_of_sub_messages
            except OSError as exc:
                logger.debug(exc, exc_info=True)
            return 0

        return sum(safe_count(folder) for folder in self.folders())

    @staticmethod
    def format_message(message: pypff.message, with_headers: bool = True) -> str:
        """Formats a pypff.message object into an RFC822 compliant string

        Args:
            message: A pypff.message object
            with_headers: whether to include the headers in the output

        Returns:
            A string
        """

        body = message.plain_text_body or message.rtf_body or message.html_body
        headers = (
            with_headers
            and message.transport_headers
            and message.transport_headers.strip()
            or ""
        )

        # If there is no message body return a string with only the headers and no "Body-Type:" label
        if not body:
            return headers

        body = decode(body).strip()

        return f"{headers}Body-Type: plain-text\r\n\r\n{body}"

    @staticmethod
    def get_message_body(message: pypff.message) -> Tuple[str, Optional[BodyType]]:
        """Takes a pypff.message object and returns a body and body type

        Args:
            message: A pypff.message object

        Returns:
            A string and a body type
        """

        # Try the plain text body first
        if message.plain_text_body:
            return message.plain_text_body, BodyType.PLAIN

        if message.rtf_body:
            return message.rtf_body, BodyType.RTF

        if message.html_body:
            return message.html_body, BodyType.HTML

        return "", None

    @staticmethod
    def get_message_headers(message: pypff.message) -> Optional[str]:
        """Takes a pypff.message object and returns its headers

        Args:
            message: A pypff.message object

        Returns:
            A string
        """

        return message.transport_headers

    def get_attachment_metadata(
        self, message: pypff.message
    ) -> List[AttachmentMetadata]:
        """
        Returns the metadata of all attachments in a given message
        """
        # pylint: disable=broad-except

        res = []

        for attachment in message.attachments:
            if attachment.name:
                try:
                    mime_type = self._get_mime_type(attachment) or guess_mime_type(
                        attachment.name
                    )

                    if mime_type is None:
                        # Expected, low severity
                        logger.debug(
                            f"No MIME type found for attachment {attachment.name} in file {self.filepath}, message {message.identifier}"
                        )

                except Exception as exc:
                    # Unexpected, higher severity
                    logger.info(
                        f"Error retrieving MIME type for attachment {attachment.name} in file {self.filepath}, message {message.identifier}"
                    )
                    logger.debug(exc, exc_info=True)

                    mime_type = None

                res.append(
                    AttachmentMetadata(
                        name=attachment.name,
                        mime_type=mime_type,
                        size=attachment.size,
                    )
                )

        return res

    def _get_mime_type(self, attachment: pypff.attachment) -> Optional[str]:

        entries = attachment.record_sets[0].entries

        # Try known positions first
        for i in self._mime_indices:
            try:
                res = self._decode_mime_type(entries[i].data)
                if res:
                    self._mime_indices[i] += 1
                    self._sort_mime_indices()

                    return res

            # If i is out of bounds pypff raises ValueError instead of IndexError
            except ValueError:
                pass

        # Try the rest
        for i, entry in enumerate(entries):
            if i not in self._mime_indices:
                res = self._decode_mime_type(entry.data)
                if res:
                    self._mime_indices[i] += 1
                    self._sort_mime_indices()

                    return res

        return None

    def _decode_mime_type(self, data: bytes) -> Optional[str]:

        for encoding in self._encodings:
            try:
                mime_type = data.decode(encoding).rstrip("\0")

                if mime_type.split("/", maxsplit=1)[0].lower() in MIME_TYPE_REGISTRIES:

                    # re-order encodings to try this one first
                    if self._encodings[0] != encoding:
                        self._encodings = [
                            encoding,
                            *[e for e in self._encodings if e != encoding],
                        ]

                    return mime_type

            except AttributeError:
                return None

            except UnicodeDecodeError:
                pass

        return None

    def _sort_mime_indices(self):
        self._mime_indices = defaultdict(
            int, sorted(self._mime_indices.items(), key=lambda x: x[1], reverse=True)
        )

    @staticmethod
    def get_message_date(message: pypff.message) -> datetime:
        return message.get_client_submit_time()


def pff_msg_to_string(message: pypff.message) -> str:
    """
    Serializes a pff.message object to a string
    """

    headers = message.transport_headers or ""
    body = decode(
        message.plain_text_body or message.rtf_body or message.html_body or ""
    )

    return f"{headers.strip()}\r\n\r\n{body.strip()}"
