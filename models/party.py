from sqlalchemy import Integer, Column, String, Float, Boolean, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship

from .base import Base

UserParty = Table(
    'party_participations', Base.metadata,
    Column('user_id', ForeignKey('users.user_id'), primary_key=True),
    Column('party_id', ForeignKey('parties.party_id'), primary_key=True)
)


class Party(Base):  # type: ignore
    __tablename__ = 'parties'

    party_id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    location = Column(String)
    date = Column(String)
    organizer_id = Column(Integer, ForeignKey('users.user_id'))
    cost = Column(Float)
    done = Column(Boolean)
    date_datetime = Column(DateTime)
    actual_datetime = Column(DateTime, default=None)

    # Relations
    users = relationship('User', secondary=UserParty, back_populates='parties')
    organizer = relationship('User', back_populates='organized_parties')

    def __repr__(self) -> str:
        date_text = ""
        if self.actual_datetime is not None:
            date_text = f'{self.actual_datetime.strftime("%A")} {self.actual_datetime.date()}'
        return f'Суета от {self.organizer}\n' \
               f'Дата: {date_text}\n' \
               f'Описание: {self.description}'


class Idea(Base):
    __tablename__ = 'ideas'

    idea_id = Column(Integer, primary_key=True)
    description = Column(String)

    def __repr__(self) -> str:
        return f'Idea: {self.description}'
