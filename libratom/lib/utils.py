# pylint: disable=missing-docstring

import mimetypes
import re
from typing import AnyStr

from bs4 import BeautifulSoup
from striprtf.striprtf import rtf_to_text

from libratom.lib.constants import BodyType

mimetypes.init()


def decode(content: AnyStr) -> str:
    if isinstance(content, bytes):
        return str(content, encoding="utf-8", errors="replace")

    return content


def cleanup_message_body(
    body: AnyStr, body_type: BodyType, size_threshold: int = 0
) -> str:
    # Decode first
    body = decode(body)

    if body_type is BodyType.RTF:
        # Strip formatting
        body = rtf_to_text(body)

    elif body_type is BodyType.HTML:
        # Strip markup
        body = BeautifulSoup(body, "html.parser").get_text()

    # Strip what might be lines of base64 encoded data
    if len(body) > size_threshold:
        body = re.sub(r"^[>\s]*[A-Za-z0-9+/]{76,}\n?", "", body, flags=re.MULTILINE)

    # Strip uuencoded attachments
    if len(body) > size_threshold:
        body = re.sub(r"begin [0-7]{3}.*?end", "", body, flags=re.DOTALL)

    # Strip notes/calendar data
    if len(body) > size_threshold:
        body = re.sub(
            r"<(OMNI|omni)([^>]*?)>.*?</\1\2>(\s)*", "", body, flags=re.DOTALL
        )

    return body.strip()


def guess_mime_type(name: str) -> str:
    return mimetypes.guess_type(name, strict=False)[0]
