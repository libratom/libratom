# pylint: disable=too-few-public-methods,missing-docstring,invalid-name

from sqlalchemy import Column, Integer, String

from libratom.lib.database import Base


class FileReport(Base):
    __tablename__ = "file_report"

    id = Column(Integer, primary_key=True)
    path = Column(String)
    name = Column(String)
    size = Column(Integer)
    md5 = Column(String)
    sha256 = Column(String)

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