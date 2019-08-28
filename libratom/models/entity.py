# pylint: disable=too-few-public-methods,missing-docstring,invalid-name

from sqlalchemy import Column, ForeignKey, Integer, String

from libratom.lib.database import Base
from libratom.models.file_report import FileReport
from libratom.models.message import Message


class Entity(Base):
    __tablename__ = "entity"

    id = Column(Integer, primary_key=True)
    text = Column(String)
    label_ = Column(String)
    filepath = Column(String)
    message_id = Column(Integer, ForeignKey(Message.id))
    file_report_id = Column(Integer, ForeignKey(FileReport.id))

    def __str__(self):
        column_names = [col.key for col in self.__table__.columns]
        return " ".join([f"{name}: {getattr(self, name)}" for name in column_names])
