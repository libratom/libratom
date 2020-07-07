# pylint: disable=missing-docstring

import re
from typing import AnyStr

from bs4 import BeautifulSoup
from striprtf.striprtf import rtf_to_text

from libratom.lib.constants import RATOM_SPACY_MODEL_MAX_LENGTH, BodyType


def decode(content: AnyStr) -> str:
    if isinstance(content, bytes):
        return str(content, encoding="utf-8", errors="replace")

    return content


def sanitize_message_body(body: AnyStr, body_type: BodyType) -> str:
    # Decode first
    body = decode(body)

    if body_type is BodyType.RTF:
        # Strip formatting
        body = rtf_to_text(body)

    elif body_type is BodyType.HTML:
        # Strip markup
        body = BeautifulSoup(body, "html.parser").get_text()

    if len(body) > RATOM_SPACY_MODEL_MAX_LENGTH:
        # Strip uuencoded attachments
        body = re.sub("begin [0-7]{3}.*?end", "", body, flags=re.DOTALL)

    if len(body) > RATOM_SPACY_MODEL_MAX_LENGTH:
        # Strip base64 encoded lines
        body = re.sub(r"^[>\s]*[A-Za-z0-9+/]{76,}\n?", "", body, flags=re.MULTILINE)

    return body
