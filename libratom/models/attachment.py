# pylint: disable=too-few-public-methods,missing-docstring,invalid-name

from sqlalchemy import Column, ForeignKey, Integer, LargeBinary, String

from libratom.lib.database import Base


class Attachment(Base):
    __tablename__ = "attachment"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    mime_type = Column(String)
    size = Column(Integer)
    content = Column(LargeBinary)
    message_id = Column(Integer, ForeignKey("message.id"))
    file_report_id = Column(Integer, ForeignKey("file_report.id"))
