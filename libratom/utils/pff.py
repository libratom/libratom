import logging
from collections import deque
from io import IOBase
from pathlib import Path

import pypff

logger = logging.getLogger(__name__)


class PffArchive:
    def __init__(self, file=None):
        self.data = pypff.file()

        if file:
            self.load(file)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.data.close()

    def load(self, file):
        if isinstance(file, IOBase):
            self.data.open_file_object(file)
        elif isinstance(file, (Path, str)):
            self.data.open(str(file), "rb")
        else:
            raise TypeError(f"Unable to load {file} of type {type(file)}")

    def folders(self, bfs=True):
        folders = deque([self.data.root_folder])

        while folders:
            folder = folders.pop()

            yield folder

            if bfs:
                folders.extendleft(folder.sub_folders)
            else:
                folders.extend(folder.sub_folders)

    def messages(self, bfs=True):
        for folder in self.folders(bfs):
            for message in folder.sub_messages:
                yield message
