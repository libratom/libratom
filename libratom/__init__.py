"""
Set of Python tools for the RATOM project
"""

try:
    from importlib.metadata import version

    __version__ = version(__package__ or __name__)
except ImportError:
    # Fallback for Python < 3.8
    from importlib_metadata import version

    __version__ = version(__package__ or __name__)
