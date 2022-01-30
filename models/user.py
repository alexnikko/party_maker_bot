from sqlalchemy import Integer, Column, String, Boolean
from sqlalchemy.orm import relationship

from .base import Base
from .party import UserParty


class User(Base):  # type: ignore
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    username = Column(String)
    full_name = Column(String)
    is_organizer = Column(Boolean)
    total_declines = Column(Integer, default=0)
    state = Column(Integer, default=0)

    # Relations
    parties = relationship('Party', secondary=UserParty, back_populates='users')
    organized_parties = relationship('Party', back_populates='organizer')

    def __repr__(self) -> str:
        return f'{self.username}'


class UserQueue(Base):  # type: ignore
    __tablename__ = 'user_queue'

    row_id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    has_plan = Column(Boolean)

    def __repr__(self) -> str:
        return f'<UserQueue user_id={self.user_id}, has_plan={self.has_plan}>'
