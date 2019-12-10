# pylint: disable=too-few-public-methods,missing-docstring,invalid-name

from operator import attrgetter

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from libratom.lib.database import Base


class FileReport(Base):
    __tablename__ = "file_report"

    id = Column(Integer, primary_key=True)
    path = Column(String)
    name = Column(String)  # for convenience
    size = Column(Integer)
    md5 = Column(String)
    sha256 = Column(String)
    error = Column(String)
    msg_count = Column(
        Integer
    )  # should be equal to len(self.messages) after processing if the file had no issues
    messages = relationship(
        "Message", backref="file_report", order_by="Message.processing_start_time"
    )
    entities = relationship("Entity", backref="file_report")
    attachments = relationship("Attachment", backref="file_report")

    @property
    def processing_start_time(self):
        try:
            return self.messages[0].processing_start_time
        except IndexError:
            return None

    @property
    def processing_end_time(self):
        try:
            return max(
                self.messages, key=attrgetter("processing_end_time")
            ).processing_end_time
        except ValueError:
            return None

    @property
    def processing_wall_time(self):
        try:
            return self.processing_end_time - self.processing_start_time
        except TypeError:
            return None
