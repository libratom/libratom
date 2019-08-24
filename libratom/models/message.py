# pylint: disable=too-few-public-methods,missing-docstring,invalid-name

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True)
    processing_start_time = Column(DateTime)
    processing_end_time = Column(DateTime)
