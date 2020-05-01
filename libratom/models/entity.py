# pylint: disable=too-few-public-methods,missing-docstring,invalid-name,no-member

from sqlalchemy import Column, ForeignKey, Integer, String

from libratom.lib.database import Base


class Entity(Base):
    __tablename__ = "entity"

    id = Column(Integer, primary_key=True)
    text = Column(String)
    label_ = Column(String)
    filepath = Column(String)
    message_id = Column(Integer, ForeignKey("message.id"))
    file_report_id = Column(Integer, ForeignKey("file_report.id"))

    def __str__(self):
        column_names = [col.key for col in self.__table__.columns]
        return " ".join([f"{name}: {getattr(self, name)}" for name in column_names])
