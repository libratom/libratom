"""
Custom exceptions
"""


class RatomException(Exception):
    """
    Base exception class for libratom's custom exceptions
    """


class FileTypeError(RatomException):
    """
    File type not supported
    """
