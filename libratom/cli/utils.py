# pylint: disable=unused-argument,too-few-public-methods,arguments-differ
"""
Command-line interface utilities
"""

from contextlib import AbstractContextManager
from pathlib import Path

import click


class PathPath(click.Path):
    """
    A Click path argument that returns a pathlib Path, not a string

    https://github.com/pallets/click/issues/405#issuecomment-470812067
    """

    def convert(self, value, param, ctx):
        return Path(super().convert(value, param, ctx))


class MockContext(AbstractContextManager):
    """
    A no-op context manager for use in python 3.6 and newer
    It accepts an arbitrary number of keyword arguments and returns an object whose attributes are all None

    Modified from https://github.com/python/cpython/blob/v3.7.4/Lib/contextlib.py#L685-L703
    """

    def __init__(self, **__):
        pass

    def __getattribute__(self, item):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *excinfo):
        pass


def validate_out_path(ctx, param, value: Path) -> Path:
    """
    Callback for click commands that checks that an output file doesn't already exist
    """

    if value.is_file():
        raise click.BadParameter(f'File "{value}" already exists.')

    return value
