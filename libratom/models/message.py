# pylint: disable=too-few-public-methods,missing-docstring,invalid-name

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from libratom.lib.database import Base
from libratom.models.file_report import FileReport


class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True)
    pff_identifier = Column(Integer)
    processing_start_time = Column(DateTime)
    processing_end_time = Column(DateTime)
    file_report_id = Column(Integer, ForeignKey(FileReport.id))
    entities = relationship("Entity", backref="message")
