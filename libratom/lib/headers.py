"""
Header fields parsing utilities
"""

import csv
from importlib import resources
from typing import Dict

from sqlalchemy.orm.session import Session

from libratom import data
from libratom.models import HeaderFieldType


def populate_header_field_types(session: Session) -> None:
    """
    Create and populate the header_field_type table according to:
    https://www.iana.org/assignments/message-headers/message-headers.xhtml
    """

    with resources.path(data, "perm-headers.csv") as path, path.open(mode="r") as f:
        header_field_types = [
            HeaderFieldType(name=row["Header Field Name"])
            for row in csv.DictReader(f)
            if row["Protocol"] in {"mail", "MIME"}
        ]

    session.add_all(header_field_types)
    session.commit()


def get_header_field_type_mapping(session: Session) -> Dict[str, HeaderFieldType]:
    """
    Cache and map the contents of the header field type table in memory before parsing header fields
    """

    return {hft.name.lower(): hft for hft in session.query(HeaderFieldType).all()}
