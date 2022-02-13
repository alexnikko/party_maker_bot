from sqlalchemy import Column, Integer, String, Boolean, Float

from .base import Base


class Planned(Base):  # type: ignore
    __tablename__ = 'planned'

    day = Column(String, primary_key=True, autoincrement=False)
    is_planned = Column(Boolean, default=False)


class SchedulerInfo(Base):  # type: ignore
    __tablename__ = 'scheduler'

    day = Column(String, primary_key=True, autoincrement=False)
    user_id = Column(Integer, primary_key=True, autoincrement=False)
    is_asked = Column(Boolean, default=False)
    is_answered = Column(Boolean, default=False)
    is_agree = Column(Boolean, default=False)
    is_declined = Column(Boolean, default=False)
    response_count = Column(Integer, default=0)
    last_request_time = Column(Float, default=0)


class Poll(Base):  # type: ignore
    __tablename__ = 'polls'

    poll_id = Column(String, primary_key=True)
    party_id = Column(Integer, default=None)
    message_id = Column(Integer, default=None)
    poll_type = Column(String, default=None)
    poll_type_id = Column(Integer, default=None)  # 0 - start

    def __repr__(self) -> str:
        def filter_attr(attr):
            return not callable(getattr(self, attr)) \
                   and not attr.startswith('__') \
                   and not attr.startswith('_') \
                   and attr not in ['metadata', 'registry']

        fields = [attr for attr in dir(self) if filter_attr(attr)]
        return 'Poll:\n' + '\n'.join([f'{field}={getattr(self, field)}' for field in fields])
