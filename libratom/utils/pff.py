"""
PFF parsing utilities. Requires libpff.
"""

import logging
from collections import deque
from io import IOBase
from pathlib import Path

import pypff

logger = logging.getLogger(__name__)


class PffArchive:
    """Wrapper class around pypff.file

    Provides methods for manipulating a PFF archive
    """

    def __init__(self, file=None):
        self.data = pypff.file()

        if file:
            self.load(file)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.data.close()

    def load(self, file):
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

    def folders(self, bfs=True):
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

    def messages(self, bfs=True):
        """Generator function to iterate over the archive's messages

        Args:
            bfs: Whether the folder tree should be walked breadth first

        Yields:
            A pypff.message object
        """

        for folder in self.folders(bfs):
            for message in folder.sub_messages:
                yield message

    @staticmethod
    def format_message(message):
        """Formats a pypff.message object into an RFC822 compliant string

        Args:
            message: A pypff.message object

        Returns:
            A string
        """
        body = message.plain_text_body or message.html_body or message.rtf_body

        if isinstance(body, bytes):
            body = str(body, encoding="utf-8", errors="replace")

        return f"{message.transport_headers}Body-Type: plain-text\r\n\r\n{body.strip()}"
