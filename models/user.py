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

    # Relations
    parties = relationship('Party', secondary=UserParty, back_populates='users')
    organized_parties = relationship('Party', back_populates='organizer')

    def __repr__(self) -> str:
        return f'<User user_id={self.user_id}, username={self.username}, ' \
               f'full_name={self.full_name}, is_organizer={self.is_organizer}, ' \
               f'total_declines={self.total_declines}>'
