"""
Non-code files
"""

import json

try:
    from importlib import resources
except ImportError:
    # backport version for Python 3.6
    import importlib_resources as resources


# Load JSON data for direct access
with resources.path(__name__, "media_types.json") as media_types_file, open(
    media_types_file, "r"
) as fp:
    MIME_TYPES = set(json.load(fp))

MIME_TYPE_REGISTRIES = {mime_type.split("/", maxsplit=1)[0] for mime_type in MIME_TYPES}

with resources.path(__name__, "eml_dump_input.schema.json") as schema_file, open(
    schema_file
) as schema_fp:
    EML_DUMP_INPUT_SCHEMA = json.load(schema_fp)
