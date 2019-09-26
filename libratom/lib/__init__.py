# pylint: disable=missing-docstring,broad-except

from pathlib import Path
from typing import Optional, Union

from libratom.lib.mbox import MboxArchive
from libratom.lib.pff import PffArchive


def open_mail_archive(
    file: Union[Path, str]
) -> Optional[Union[PffArchive, MboxArchive]]:

    try:
        return PffArchive(file)
    except Exception:
        pass

    try:
        return MboxArchive(file)
    except Exception:
        pass

    raise RuntimeError(f"Unable to open {file} as either pst or mbox archive.")
