# pylint: disable=too-few-public-methods,missing-docstring,invalid-name

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from libratom.lib.database import Base


class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True)
    pff_identifier = Column(Integer)
    date = Column(DateTime)
    headers = Column(String)
    body = Column(String)
    processing_start_time = Column(DateTime)
    processing_end_time = Column(DateTime)
    file_report_id = Column(Integer, ForeignKey("file_report.id"))
    entities = relationship("Entity", backref="message")
    attachments = relationship("Attachment", backref="message")
    header_fields = relationship("HeaderField", backref="message")
