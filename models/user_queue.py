from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.orm import relationship

from .base import Base


class UserQueue(Base):  # type: ignore
    __tablename__ = 'user_queue'

    row_id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    has_plan = Column(Boolean)

    def __repr__(self) -> str:
        return f'<UserQueue user_id={self.user_id}, has_plan={self.has_plan}>'
