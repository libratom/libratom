"""
Non-code files
"""

import json

try:
    from importlib import resources
except ImportError:
    # backport version for Python 3.6
    import importlib_resources as resources


with resources.path(__name__, "media_types.json") as media_types_file:
    with open(media_types_file, "r") as fp:
        MIME_TYPES = json.load(fp)
