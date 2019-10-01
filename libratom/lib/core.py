# pylint: disable=missing-docstring,broad-except

from pathlib import Path
from typing import Optional, Set, Union

from libratom.lib import MboxArchive, PffArchive
from libratom.lib.exceptions import FileTypeError


def open_mail_archive(path: Path) -> Optional[Union[PffArchive, MboxArchive]]:

    extension_type_mapping = {".pst": PffArchive, ".mbox": MboxArchive}

    try:
        archive_class = extension_type_mapping[path.suffix]
    except KeyError:
        raise FileTypeError(f"Unable to open {path}. Unsupported file type.")

    return archive_class(path)


def get_set_of_files(path: Path) -> Set[Path]:
    if path.is_dir():
        return set(path.glob("**/*.pst")).union(set(path.glob("**/*.mbox")))

    return {path}
