# pylint: disable=missing-docstring,broad-except

from pathlib import Path
from typing import Optional, Set, Union

from libratom.lib import MboxArchive, PffArchive


def open_mail_archive(
    file: Union[Path, str]
) -> Optional[Union[PffArchive, MboxArchive]]:

    archive_classes = [PffArchive, MboxArchive]

    for cls in archive_classes:
        try:
            return cls(file)
        except Exception:
            pass

    raise RuntimeError(f"Unable to open {file} as any of {archive_classes}.")


def get_set_of_files(path: Path) -> Set[Path]:
    if path.is_dir():
        return set(path.glob("**/*.pst")).union(set(path.glob("**/*.mbox")))

    return {path}
