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
