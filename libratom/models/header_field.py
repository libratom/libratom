# pylint: disable=too-few-public-methods,missing-docstring

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from libratom.lib.database import Base


class HeaderFieldType(Base):
    __tablename__ = "header_field_type"

    id = Column(Integer, primary_key=True)
    name = Column(String)


class HeaderField(Base):
    __tablename__ = "header_field"

    id = Column(Integer, primary_key=True)
    value = Column(String)
    header_field_type_id = Column(ForeignKey("header_field_type.id"), nullable=False)
    header_field_type = relationship("HeaderFieldType")
    message_id = Column(ForeignKey("message.id"), nullable=False)

    @property
    def name(self):
        return self.header_field_type.name
