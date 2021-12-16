import asyncio
import aioschedule
from datetime import datetime, timedelta
from collections import defaultdict

day_user = tuple[str, int]

from aiogram import Bot, types, filters
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

import credentials

from sqlalchemy import select
from models.base import clear_session
from models.core import create_user, select_all_users, add_user_to_queue, delete_user, get_info_for_scheduler,\
    roll_queue
from models.user import User
from models.user_queue import UserQueue
from models.scheduler import Planned, SchedulerInfo

import warnings

warnings.filterwarnings('ignore')

# import logging

# logging.basicConfig(level=logging.DEBUG)

DEBUG = True

if DEBUG:
    MAX_RESPONSE_COUNT = 2
    MAX_RESPONSE_SECONDS = 20
    MAX_TOTAL_DECLINES = 3
else:
    MAX_RESPONSE_COUNT = 2
    MAX_RESPONSE_SECONDS = 1 * 60 * 60
    MAX_TOTAL_DECLINES = 1

bot = Bot(token=credentials.token)
dp = Dispatcher(bot)
session = clear_session()

# buttons
button_yes = types.InlineKeyboardButton('Yes', callback_data='button_yes')
button_no = types.InlineKeyboardButton('No', callback_data='button_no')
answer_kb = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
answer_kb.add(button_yes)
answer_kb.add(button_no)


@dp.callback_query_handler(lambda c: c.data == 'button_yes')
async def process_callback_button_yes(callback_query: types.CallbackQuery):
    # print('callback_query', callback_query)
    day = callback_query.message.text.split()[-1]
    user_id = callback_query.from_user.id
    message_time = callback_query.message.date.timestamp()
    answer_time = datetime.now().timestamp()
    # print(day, user_id, message_time, answer_time, answer_time - message_time, sep='\n')
    if answer_time - message_time > MAX_RESPONSE_SECONDS:
        await bot.answer_callback_query(callback_query.id)
        return
    scheduler_info = session.execute(select(SchedulerInfo).filter_by(day=day, user_id=user_id)).scalar()
    scheduler_info.is_answered = True
    scheduler_info.is_agree = True

    planned_day = session.execute(select(Planned).filter_by(day=day)).scalar()
    planned_day.is_planned = True
    session.commit()

    print('CURRENT QUEUE DB STATE:')
    for user_in_queue in list(session.execute(select(UserQueue)).scalars()):
        print(user_in_queue)
    roll_queue(user_id, session=session)
    print('CURRENT QUEUE DB STATE:')
    for user_in_queue in list(session.execute(select(UserQueue)).scalars()):
        print(user_in_queue)
    await bot.send_message(callback_query.from_user.id, f'Спасибо, теперь вы главный суетолог {day}')


@dp.callback_query_handler(lambda c: c.data == 'button_no')
async def process_callback_button_no(callback_query: types.CallbackQuery):
    # print('callback_query', callback_query)
    day = callback_query.message.text.split()[-1]
    user_id = callback_query.from_user.id
    message_time = callback_query.message.date.timestamp()
    answer_time = datetime.now().timestamp()
    # print(day, user_id, message_time, answer_time, answer_time - message_time, sep='\n')
    if answer_time - message_time > MAX_RESPONSE_SECONDS:
        await bot.answer_callback_query(callback_query.id)
        return
    scheduler_info = session.execute(select(SchedulerInfo).filter_by(day=day, user_id=user_id)).scalar()
    scheduler_info.is_answered = True
    scheduler_info.is_agree = False
    session.commit()
    await bot.send_message(callback_query.from_user.id, f'Спасибо за ответ.')


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    result = await bot.send_poll(
        chat_id=message.chat.id,
        question='Кем вы хотите быть?',
        options=['Суетологом! (организатором мероприятий)', 'Тусером! (участником мероприятий)'],
        is_anonymous=False
    )
    print(result)


@dp.poll_answer_handler()
async def some_poll_answer_handler(poll_answer: types.PollAnswer):
    # print(poll_answer)
    tg_user = poll_answer['user']
    user_id = tg_user.id
    username = tg_user.username
    full_name = tg_user.full_name
    is_retract = not poll_answer['option_ids']
    if not is_retract:
        is_organizer = poll_answer['option_ids'][0] == 0
        create_user(user_id, username, full_name, is_organizer, session=session)

        if is_organizer:
            add_user_to_queue(user_id=user_id, has_plan=False, session=session)
    else:
        # delete user from users DB and from queue if he was organizer
        delete_user(user_id, session=session)

    # print('CURRENT USER DB STATE:')
    # for user in list(select_all_users(session=session)):
    #     print(user)
    #
    # print('CURRENT QUEUE DB STATE:')
    # for user_in_queue in list(session.execute(select(UserQueue)).scalars()):
    #     print(user_in_queue)


@dp.message_handler()
async def create_deeplink(message: types.Message):
    print(message)
    await bot.send_message(message.chat.id, reply_to_message_id=message.message_id,
                           text=f'THANK YOU SO MUCH FOR YOU MESSAGE, DEAR {message.from_user.mention}')


def get_next_4_weekends() -> list[str]:
    weekends = []
    current_day = datetime.now().date()
    delta = timedelta(days=1)

    while len(weekends) != 4:
        if current_day.weekday() == 5:
            weekends.append(current_day.strftime("%d/%m/%Y"))
        current_day += delta

    return weekends


async def match():
    """
    Просыпается скедулер. Скедулер проверяет текущий час, если нерабочее время, то засыпает
    тут что-то про считывание из базы данных
    генерируем следующие 4 недели (субботы)
    идем по субботам, если суббота запланирована, то скипаем её
    если суббота незапланирована, то идём по очереди из организаторов.
    Спрашиваем первого организатора согласие. Напоминаем, ему, что нужно ответить каждый час.
    Если слишком много раз (долго) не отвечает, то баним его.
    Если ответил и согласен, то отправляем уведомление в группу и переходим к следующему дню
    Если не согласен, то увеличиваем счетчик отказов и если что баним
    :return:
    """
    current_time = datetime.now()
    if not DEBUG and (current_time.hour < 12 or current_time.hour > 20):
        return

    if DEBUG:
        print('WOKE UP')

    # planned: dict[str, bool] = {}
    # queue: list[int] = []
    # asked: dict[tuple[str, int], bool] = {}
    # answered: dict[tuple[str, int], bool] = {}
    # agree: dict[tuple[str, int], bool] = {}
    # declined: dict[tuple[str, int], bool] = defaultdict(bool)
    # count_response: dict[tuple[str, int], int] = defaultdict(int)
    # last_request_time: dict[tuple[str, int], float] = {}
    # total_declines: dict[int, int] = defaultdict(int)

    planned, queue, asked, answered, agree, \
    declined, count_response, last_request_time, total_declines = get_info_for_scheduler(session=session)

    if DEBUG:
        print(queue)

    next_weekends = get_next_4_weekends()  # [day1, day2, day3, day4]
    if DEBUG:
        print(next_weekends)
    for day in next_weekends:
        if day not in planned:
            planned[day] = False
            planned_day = Planned(day=day)
            session.add(planned_day)
            session.commit()
        if DEBUG:
            print(day)
        planned_day = session.execute(select(Planned).filter_by(day=day)).scalar()
        if DEBUG:
            print(day, planned[day])
        if planned[day]:
            continue
        for person in queue:
            scheduler_info = session.execute(select(SchedulerInfo).filter_by(day=day, user_id=person)).scalar()
            if scheduler_info is None:
                scheduler_info = SchedulerInfo(day=day, user_id=person)
                session.add(scheduler_info)
                session.commit()
            user = session.execute(select(User).filter_by(user_id=person)).scalar()
            if DEBUG:
                print(user)
            if declined[day, person]:
                continue
            if not asked[day, person]:
                asked[day, person] = True
                count_response[day, person] += 1
                last_request_time[day, person] = current_time.timestamp()

                scheduler_info.is_asked = True
                scheduler_info.response_count += 1
                scheduler_info.last_request_time = current_time.timestamp()
                session.commit()
                # todo: send message to person (question)
                print('SENDING MESSAGE')
                await bot.send_message(person,
                                       text=f'Hello, can you be the organizer?\n'
                                            f'Expected date: {day}',
                                       reply_markup=answer_kb)
                return
            if not answered[day, person]:
                if count_response[day, person] > MAX_RESPONSE_COUNT:
                    # todo: ban user because no answer for a long time
                    answered[day, person] = True

                    scheduler_info.is_answered = True
                    session.commit()
                elif current_time.timestamp() - last_request_time[day, person] < MAX_RESPONSE_SECONDS:
                    return
                # todo: send message to person
                count_response[day, person] += 1
                last_request_time[day, person] = current_time.timestamp()

                scheduler_info.response_count += 1
                scheduler_info.last_request_time = current_time.timestamp()
                session.commit()
                return
            elif agree[day, person]:
                planned[day] = True
                answered[day, person] = True

                planned_day.is_planned = True
                scheduler_info.is_answered = True
                session.commit()
                # todo: send message to the group about incoming party and its organizer
                # todo: dequeue and enqueue person again (to the tail of queue)
                # todo: check if organizer was last time organizer too
                return
            else:
                declined[day, person] = True
                total_declines[person] += 1

                scheduler_info.is_declined = True
                user.total_declines += 1
                session.commit()
                if total_declines[person] > MAX_TOTAL_DECLINES:
                    # todo: ban person
                    pass
                else:
                    # todo: dequeue and enqueue person again (to the tail of queue)
                    pass

        # todo: send message to the group about default party
        if queue:
            planned[day] = True
            planned_day.is_planned = True
            session.commit()


async def scheduler():
    if DEBUG:
        aioschedule.every(5).seconds.do(match)
    else:
        aioschedule.every(5).minutes.do(match)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(_):
    asyncio.create_task(scheduler())


if __name__ == '__main__':
    # user1 = UserQueue(user_id=1, has_plan=True)
    # user2 = UserQueue(user_id=2, has_plan=True)
    # user3 = UserQueue(user_id=3, has_plan=False)
    #
    # session.add(user1)
    # session.add(user2)
    # session.add(user3)
    # session.commit()
    # print('CURRENT QUEUE DB STATE:')
    # for user_in_queue in list(session.execute(select(UserQueue)).scalars()):
    #     print(user_in_queue)
    #
    # session.delete(user1)
    # print('CURRENT QUEUE DB STATE:')
    # for user_in_queue in list(session.execute(select(UserQueue)).scalars()):
    #     print(user_in_queue)
    # session.add(UserQueue(user_id=1, has_plan=True))
    # print('CURRENT QUEUE DB STATE:')
    # for user_in_queue in list(session.execute(select(UserQueue)).scalars()):
    #     print(user_in_queue)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
