# pylint: disable=missing-docstring

from abc import ABC, abstractmethod
from typing import Any, Generator


class Archive(ABC):
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
