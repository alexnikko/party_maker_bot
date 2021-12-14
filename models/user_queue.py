from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship

from base import Base


class UserQueue(Base):  # type: ignore
    __tablename__ = 'user_queue'

    user_id = Column(String, primary_key=True)
    has_plan = Column(Boolean)

    def __repr__(self) -> str:
        return f'<UserQueue user_id={self.user_id}, has_plan={self.has_plan}>'
