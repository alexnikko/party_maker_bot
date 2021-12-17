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

    # Relations
    users = relationship('User', secondary=UserParty, back_populates='parties')
    organizer = relationship('User', back_populates='organized_parties')

    def __repr__(self) -> str:
        return f'<Party party_id={self.party_id}, title={self.title}, description={self.description}, ' \
               f'location={self.location}, date={self.date}, organizer_id={self.organizer_id}, ' \
               f'cost={self.cost}, done={self.done}>'


class Idea(Base):
    __tablename__ = 'ideas'

    idea_id = Column(Integer, primary_key=True)
    description = Column(String)

    def __repr__(self) -> str:
        return f'Idea: {self.description}'
