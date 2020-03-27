"""
Non-code files
"""

import json

try:
    from importlib import resources
except ImportError:
    # backport version for Python 3.6
    import importlib_resources as resources


# Load mime types for direct access
with resources.path(__name__, "media_types.json") as media_types_file, open(
    media_types_file, "r"
) as fp:
    MIME_TYPES = set(json.load(fp))
