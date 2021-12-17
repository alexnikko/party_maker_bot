from sqlalchemy import select

from .base import Session
from .user import User, UserQueue
from .party import Party, Idea
from .scheduler import Planned, SchedulerInfo, Poll

from datetime import datetime
from collections import defaultdict

composite_key = tuple[str, int]
composite_mapping_bool = dict[composite_key, bool]
composite_mapping_int = dict[composite_key, int]
composite_mapping_float = dict[composite_key, float]


def create_user(user_id: int, username: str, full_name: str, is_organizer: bool, *, session: Session) -> User:
    user = session.execute(select(User).filter_by(user_id=user_id)).scalar()
    if user:
        return user
    user = User(user_id=user_id, username=username, full_name=full_name, is_organizer=is_organizer)
    session.add(user)
    session.commit()
    return user


def delete_user(user_id: int, *, session: Session) -> bool:
    user = session.execute(select(User).filter_by(user_id=user_id)).scalar()
    if user:
        if user.is_organizer:
            user_in_queue = session.execute(select(UserQueue).filter_by(user_id=user_id)).scalar()
            session.delete(user_in_queue)
        session.delete(user)
        session.commit()
    return True


def select_all_users(*, session: Session):
    users = session.execute(select(User)).scalars()
    return users


def create_party(title: str, description: str, location: str, date: str,
                 organizer_id: int, cost: float, done: bool, *, session: Session) -> Party:
    party = Party(
        title=title,
        description=description,
        location=location,
        date=date,
        organizer_id=organizer_id,
        cost=cost,
        done=done,
        date_datetime=datetime.strptime(date, '%d/%m/%Y')
    )
    session.add(party)
    session.commit()
    return party


def create_idea(description: str, *, session: Session) -> Idea:
    idea = Idea(description=description)
    session.add(idea)
    session.commit()
    return idea


def select_ideas(*, session: Session) -> Idea:
    return session.execute(select(Idea)).scalars()


def select_all_parties(*, session: Session):
    parties = session.execute(select(Party)).scalars()
    return parties


def add_user_to_queue(user_id: int, has_plan: bool, *, session: Session) -> UserQueue:
    user = session.execute(select(UserQueue).filter_by(user_id=user_id)).scalar()
    if user:
        return user
    queue = UserQueue(user_id=user_id, has_plan=has_plan)
    session.add(queue)
    session.commit()
    return queue


def remove_user_from_queue(user_id: int, *, session: Session):
    user_in_queue = session.execute(select(UserQueue).filter_by(user_id=user_id)).scalar()
    session.delete(user_in_queue)
    session.commit()


def roll_queue(user_id: int, *, session: Session) -> UserQueue:
    user_in_queue = session.execute(select(UserQueue).filter_by(user_id=user_id)).scalar()
    user_id = user_in_queue.user_id
    has_plan = user_in_queue.has_plan

    remove_user_from_queue(user_id, session=session)
    add_user_to_queue(user_id, has_plan, session=session)
    return user_in_queue


def get_info_for_scheduler(*, session: Session):
    planned_entities = list(session.execute(select(Planned)).scalars())
    scheduler_info_entities = list(session.execute(select(SchedulerInfo)).scalars())
    queue = list(session.execute(select(UserQueue.user_id)).scalars())
    users = list(session.execute(select(User)).scalars())

    planned = {
        plan.day: plan.is_planned
        for plan in planned_entities
    }

    asked: composite_mapping_bool = defaultdict(bool)
    answered: composite_mapping_bool = defaultdict(bool)
    agree: composite_mapping_bool = defaultdict(bool)
    declined: composite_mapping_bool = defaultdict(bool)
    count_response: composite_mapping_int = defaultdict(int)
    last_request_time: composite_mapping_float = defaultdict(float)

    for scheduler_info in scheduler_info_entities:
        day, person = scheduler_info.day, scheduler_info.user_id
        asked[day, person] = scheduler_info.is_asked
        answered[day, person] = scheduler_info.is_answered
        agree[day, person] = scheduler_info.is_agree
        declined[day, person] = scheduler_info.is_declined
        count_response[day, person] = scheduler_info.response_count
        last_request_time[day, person] = scheduler_info.last_request_time

    total_declines = {
        user.user_id: user.total_declines
        for user in users
    }

    return planned, queue, asked, answered, agree, declined, count_response, last_request_time, total_declines


def create_poll(poll_id: int, party_id: int, *, session: Session):
    poll = Poll(poll_id=poll_id, party_id=party_id)
    session.add(poll)
    session.commit()
    return poll
