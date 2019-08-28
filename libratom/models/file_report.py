# pylint: disable=too-few-public-methods,missing-docstring,invalid-name

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
    messages = relationship(
        "Message", backref="file_report", order_by="Message.processing_start_time"
    )

    @property
    def message_count(self):
        pass

    @property
    def processing_start_time(self):
        pass

    @property
    def processing_end_time(self):
        pass

    @property
    def processing_wall_time(self):
        pass
