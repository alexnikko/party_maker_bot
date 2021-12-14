from sqlalchemy import select

from base import Session
from user import User
from party import Party
from user_queue import UserQueue

from datetime import datetime
from decimal import Decimal


def create_user(user_id: str, username: str, is_organizer: bool, *, session: Session) -> User:
    user = User(user_id=user_id, username=username, is_organizer=is_organizer)
    session.add(user)
    session.commit()
    return user


def select_all_users(*, session: Session):
    users = session.execute(select(User)).scalars()
    return users


def create_party(title: str, description: str, location: str, date: datetime,
                 organizer_id: str, cost: Decimal, done: bool, *, session: Session) -> Party:
    party = Party(
        title=title,
        description=description,
        location=location,
        date=date,
        organizer_id=organizer_id,
        cost=cost,
        done=done
    )
    session.add(party)
    session.commit()
    return party


def select_all_parties(*, session: Session):
    parties = session.execute(select(Party)).scalars()
    return parties


def add_user_to_queue(user_id: str, has_plan: bool, *, session: Session) -> UserQueue:
    queue = UserQueue(user_id=user_id, has_plan=has_plan)
    session.add(queue)
    session.commit()
    return queue
