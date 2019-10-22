# pylint: disable=too-few-public-methods,missing-docstring,invalid-name

from sqlalchemy import Column, Integer, String

from libratom.lib.database import Base


class Configuration(Base):
    __tablename__ = "configuration"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    value = Column(String)
