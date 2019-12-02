# pylint: disable=missing-docstring

from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Any, Generator, Iterable

AttachmentMetadata = namedtuple("AttachmentMetadata", ["name", "mime_type", "size"])


class Archive(ABC):  # pragma: no cover
    """
    Base class for various email archive formats
    """

    @abstractmethod
    def __enter__(self):
        ...

    @abstractmethod
    def __exit__(self, *_):
        ...

    @abstractmethod
    def messages(self) -> Generator[Any, None, None]:
        ...

    @property
    @abstractmethod
    def message_count(self) -> int:
        ...

    @staticmethod
    @abstractmethod
    def format_message(message: Any, with_headers: bool) -> str:
        ...

    @staticmethod
    @abstractmethod
    def get_attachment_metadata(message: Any) -> Iterable[AttachmentMetadata]:
        ...
