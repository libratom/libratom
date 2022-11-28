# pylint: disable=missing-docstring

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generator, Iterable, Optional, Tuple

from libratom.lib.constants import BodyType


@dataclass
class AttachmentMetadata:
    """
    Attachment metadata and/or payload
    """

    name: str
    mime_type: Optional[str] = None
    size: Optional[int] = None
    content: Optional[bytes] = None


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

    @abstractmethod
    def get_message_by_id(self, message_id: int) -> Optional[Any]:
        ...

    @abstractmethod
    def get_attachment_metadata(self, message: Any) -> Iterable[AttachmentMetadata]:
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
    def get_message_body(message: Any) -> Tuple[str, Optional[BodyType]]:
        ...

    @staticmethod
    @abstractmethod
    def get_message_headers(message: Any) -> Optional[str]:
        ...

    @staticmethod
    @abstractmethod
    def get_message_date(message: Any) -> datetime:
        ...
