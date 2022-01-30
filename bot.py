import asyncio
import aioschedule
from datetime import datetime, timedelta

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

import credentials

from sqlalchemy import select, func
from models.base import clear_session
from models.core import create_user, add_user_to_queue, delete_user, get_info_for_scheduler, \
    roll_queue, remove_user_from_queue, create_party, create_idea, select_ideas, create_poll
from models.party import Party
from models.user import User
from models.scheduler import Planned, SchedulerInfo, Poll

import warnings

warnings.filterwarnings('ignore')

# import logging

# logging.basicConfig(level=logging.DEBUG)
GROUP_ID = 0
DEBUG = True

MIN_IDEA_LENGTH = 3

if DEBUG:
    MAX_RESPONSE_COUNT = 2
    MAX_RESPONSE_SECONDS = 60
    MAX_RESPONSE_SECONDS_FILL_DESC = 60
    MAX_TOTAL_DECLINES = 1
else:
    MAX_RESPONSE_COUNT = 2
    MAX_RESPONSE_SECONDS = 1 * 60 * 60
    MAX_RESPONSE_SECONDS_FILL_DESC = 1 * 60 * 60
    MAX_TOTAL_DECLINES = 1

WORK_START_HOUR = 12
WORK_END_HOUR = 20

bot = Bot(token=credentials.token)
dp = Dispatcher(bot)
session = clear_session()

# TODO: set commands descriptions via code
# bot.set_my_commands()

# buttons
button_yes = types.InlineKeyboardButton('Yes', callback_data='button_yes')
button_no = types.InlineKeyboardButton('No', callback_data='button_no')
answer_kb = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
answer_kb.add(button_yes)
answer_kb.add(button_no)

# button for set_status
button_become_organizer = types.InlineKeyboardButton('Суетологом! (организатором мероприятий)',
                                                     callback_data='button_become_organizer')
button_become_chiller = types.InlineKeyboardButton('Тусером! (участником мероприятий)',
                                                   callback_data='button_become_chiller')
answer_set_status = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
answer_set_status.add(button_become_organizer)
answer_set_status.add(button_become_chiller)


@dp.callback_query_handler(lambda c: c.data == 'button_yes')
async def process_callback_button_yes(callback_query: types.CallbackQuery):
    day = callback_query.message.text.split()[-1]
    user_id = callback_query.from_user.id
    message_time = callback_query.message.date.timestamp()
    answer_time = datetime.now().timestamp()
    if answer_time - message_time > MAX_RESPONSE_SECONDS:
        await bot.answer_callback_query(callback_query.id)
        return
    scheduler_info = session.execute(select(SchedulerInfo).filter_by(day=day, user_id=user_id)).scalar()
    scheduler_info.is_answered = True
    scheduler_info.is_agree = True
    scheduler_info.response_count += 1

    planned_day = session.execute(select(Planned).filter_by(day=day)).scalar()
    planned_day.is_planned = True

    # create party
    party = create_party(
        title='', description='', location='', date=day,
        organizer_id=user_id, cost=0, done=False, session=session
    )
    session.commit()

    roll_queue(user_id, session=session)
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f'Спасибо, теперь вы главный суетолог {day}', )
    # await bot.send_message(GROUP_ID,
    #                        text=f'{callback_query.from_user.username} will be organizer of expected date: {day}\n'
    #                             f'More information will be send when organizer upload details of sueta!')
    # poll = await bot.send_poll(
    #     chat_id=GROUP_ID,
    #     question=f'Пойдёшь на мероприятие от {callback_query.from_user.username}?',
    #     options=['Я в деле!', 'Я пас :('],
    #     is_anonymous=False
    # )
    # create_poll(poll_id=poll.poll.id, party_id=party.party_id, session=session)
    # await bot.pin_chat_message(chat_id=GROUP_ID, message_id=poll.message_id)


@dp.callback_query_handler(lambda c: c.data == 'button_no')
async def process_callback_button_no(callback_query: types.CallbackQuery):
    day = callback_query.message.text.split()[-1]
    user_id = callback_query.from_user.id
    message_time = callback_query.message.date.timestamp()
    answer_time = datetime.now().timestamp()
    if answer_time - message_time > MAX_RESPONSE_SECONDS:
        await bot.answer_callback_query(callback_query.id)
        return
    scheduler_info = session.execute(select(SchedulerInfo).filter_by(day=day, user_id=user_id)).scalar()
    scheduler_info.is_answered = True
    scheduler_info.is_agree = False
    scheduler_info.response_count += 1
    scheduler_info.is_declined = True

    user = session.execute(select(User).filter_by(user_id=user_id)).scalar()
    user.total_declines += 1
    session.commit()

    if user.total_declines > MAX_TOTAL_DECLINES:
        remove_user_from_queue(user_id=user_id, session=session)
        user.is_organizer = False
        session.commit()
    else:
        roll_queue(user_id=user_id, session=session)
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f'Спасибо за ответ.')


@dp.message_handler(commands=['set_status'])
async def send_status_request(message: types.Message):
    if message.chat.id < 0:
        return
    result = await bot.send_message(
        chat_id=message.chat.id,
        text='Кем вы хотети быть?',
        reply_markup=answer_set_status
    )


# @dp.callback_query_handler(lambda c: c.data == 'button_become_organizer')
@dp.callback_query_handler(lambda c: c.data.startswith('button_become'))
async def process_callback_button_become_organizer(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = session.execute(select(User).filter_by(user_id=user_id)).scalar()
    if callback_query.data == 'button_become_organizer':
        is_organizer = True
    else:
        is_organizer = False
    if not user:
        user = User(user_id=user_id, username=callback_query.from_user.username,
                    full_name=callback_query.from_user.full_name, is_organizer=is_organizer)
        session.add(user)
        session.commit()
    else:
        user.is_organizer = is_organizer
        session.commit()
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(user_id, text='Successfully changed status')


@dp.message_handler(commands=['decline_organization'])
async def send_decline_organization_request(message: types.Message):
    if message.chat.id < 0:
        return
    user = session.execute(select(User).filter_by(user_id=message.from_user.id)).scalar()
    if not user:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not in group chat of SUETA')
        return
    if not user.is_organizer:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not organizer!')
        return
    parties = list(session.execute(select(Party).filter_by(organizer_id=user.user_id)).scalars())
    if not parties:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you have no planned parties')
        return
    available_days = [party.date for party in parties if not party.done]
    # create button for each available_party
    buttons = [
        types.InlineKeyboardButton(available_day, callback_data=f'btn_decline_{available_day}')
        for available_day in available_days
    ]
    answer_decline_organization = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for button in buttons:
        answer_decline_organization.add(button)
    await bot.send_message(
        chat_id=message.chat.id,
        text='От организации какого мероприятия вы бы хотели отказаться?',
        reply_markup=answer_decline_organization
    )


@dp.callback_query_handler(lambda c: c.data.startswith('btn_decline_'))
async def process_callback_button_decline_organization(callback_query: types.CallbackQuery):
    user = session.execute(select(User).filter_by(user_id=callback_query.from_user.id)).scalar()
    day = callback_query.data.split('_')[-1]

    scheduler_info = session.execute(select(SchedulerInfo).filter_by(day=day, user_id=user.user_id)).scalar()
    scheduler_info.is_agree = False
    scheduler_info.is_declined = True

    party = session.execute(select(Party).filter_by(date=day)).scalar()
    session.delete(party)

    planned_day = session.execute(select(Planned).filter_by(day=day)).scalar()
    planned_day.is_planned = False

    session.commit()
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(user.user_id, text='Successfully remove you from party organization')

@dp.message_handler(commands=['show_participants'])
async def send_show_participants_request(message: types.Message):
    if message.chat.id < 0:
        return
    user = session.execute(select(User).filter_by(user_id=message.from_user.id)).scalar()
    if not user:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not in group chat of SUETA')
        return
    if not user.is_organizer:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not organizer!')
        return
    parties = list(session.execute(select(Party).filter_by(organizer_id=user.user_id)).scalars())
    if not parties:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you have no planned parties')
        return
    available_days = [party.date for party in parties if not party.done]
    # create button for each available_party
    buttons = [
        types.InlineKeyboardButton(available_day, callback_data=f'btn_show_{available_day}')
        for available_day in available_days
    ]
    answer_show_participants = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for button in buttons:
        answer_show_participants.add(button)
    await bot.send_message(
        chat_id=message.chat.id,
        text='Список участников какого мероприятия вы хотите посмотреть?',
        reply_markup=answer_show_participants
    )


@dp.callback_query_handler(lambda c: c.data.startswith('btn_show_'))
async def process_callback_button_show_participants(callback_query: types.CallbackQuery):
    day = callback_query.data.split('_')[-1]

    party = session.execute(select(Party).filter_by(date=day)).scalar()
    big_message = f'Total number of participants = {len(party.users)}\n'
    for idx, user in enumerate(party.users, start=1):
        big_message += f'{idx}) {user.username}\n'

    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, text=big_message)


#  /edit
#  day1 day2 [buttons]
#  /edit day1 <your text>
@dp.message_handler(commands=['edit'])
async def send_edit_party_info_request(message: types.Message):
    if message.chat.id < 0:
        return
    user = session.execute(select(User).filter_by(user_id=message.from_user.id)).scalar()
    if not user:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not in group chat of SUETA')
        return
    if not user.is_organizer:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not organizer!')
        return
    parties = list(session.execute(select(Party).filter_by(organizer_id=user.user_id)).scalars())
    if not parties:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you have no planned parties')
        return
    nearest_party_time = min(party.date_datetime for party in parties if not party.done)
    nearest_party = session.execute(
        select(Party).filter_by(organizer_id=user.user_id).filter_by(date_datetime=nearest_party_time)).scalar()

    user.state = 1
    session.commit()
    await bot.send_message(
        chat_id=message.chat.id,
        text=f'Send me description of your party, now it is:\n'
             f'{nearest_party}',
    )





@dp.callback_query_handler(lambda c: c.data.startswith('btn_change_info_'))
async def process_callback_button_change_info(callback_query: types.CallbackQuery):
    day = callback_query.data.split('_')[-1]
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id,
                           text=f'Please, write the following command:'
                                f' "/edit_info {day} <DESCRIPTION>", where <DESCRIPTION> is your description of party')


@dp.message_handler(commands=['edit_info'])
async def send_edit_party_info_description_request(message: types.Message):
    if message.chat.id < 0:
        return
    user = session.execute(select(User).filter_by(user_id=message.from_user.id)).scalar()
    if not user:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not in group chat of SUETA')
        return
    if not user.is_organizer:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not organizer!')
        return
    tokens = message.text.split()
    if len(tokens) < 3:
        return
    day = tokens[1]
    description = ' '.join(tokens[2:])
    parties = list(session.execute(select(Party).filter_by(organizer_id=user.user_id)).scalars())
    available_days = {party.date for party in parties if not party.done}
    if day not in available_days:
        await bot.send_message(chat_id=user.user_id, text=f'Sorry, you have no that date :( {day} - WRONG DATE')
        return
    party = session.execute(select(Party).filter_by(date=day)).scalar()
    party.description = description
    session.commit()
    await bot.send_message(
        chat_id=message.chat.id,
        text=f'Успешно изменено описание на {description}'
    )
    await bot.send_message(
        chat_id=GROUP_ID,
        text=f'{message.from_user.username} изменил описания мероприятия {day} на {description}'
    )


@dp.message_handler(commands=['show_nearest'])
async def send_show_nearest_request(message: types.Message):
    nearest_party_time = session.execute(select(func.min(Party.date_datetime)).where(Party.done == False)).scalar()
    if not nearest_party_time:
        await bot.send_message(chat_id=message.chat.id, text='No parties are planned :(')
        return
    nearest_party = session.execute(select(Party).filter_by(date_datetime=nearest_party_time)).scalar()
    optional_info = ''
    if message.chat.id > 0:
        if message.from_user in nearest_party.users or message.from_user == nearest_party.organizer:
            optional_info = '\nYou are going to visit it! :)'
        else:
            optional_info = '\nYou are not going to visit it! :('

    await bot.send_message(chat_id=message.chat.id,
                           text=f'The nearest party is:\n'
                                f'{nearest_party}'
                                f'{optional_info}')


@dp.message_handler(commands=['tag_all'])
async def tag_all_request(message: types.Message):
    user_text = ' '.join(message.text.split()[1:])
    user = session.execute(select(User).filter_by(user_id=message.from_user.id)).scalar()
    if not user:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not in group chat of SUETA')
        return
    if not user.is_organizer:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not organizer!')
        return
    parties = list(session.execute(select(Party).filter_by(organizer_id=user.user_id)).scalars())
    if not parties:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you have no planned parties')
        return
    nearest_party_time = session.execute(select(func.min(Party.date_datetime)).where(Party.done == False) \
                                         .where(Party.organizer_id == user.user_id)).scalar()
    nearest_party = session.execute(select(Party).filter_by(date_datetime=nearest_party_time)).scalar()
    tag_list = [
        f'@{participant.username}'
        for participant in nearest_party.users
    ]
    await bot.send_message(
        chat_id=GROUP_ID, #message.chat.id,
        text=f'{user_text}\n'
             f'{" ".join(tag_list)}'
    )


@dp.message_handler(commands=['idea'])
async def send_idea_request(message: types.Message):
    if message.chat.id < 0:
        return
    tokens = message.text.split()
    words = tokens[1:] if len(tokens) > 1 else []
    if len(words) < MIN_IDEA_LENGTH:
        await bot.send_message(chat_id=message.chat.id,
                               text='Sorry, but your idea is too short, describe it more informative')
        return
    description = ' '.join(words)
    create_idea(description=description, session=session)
    await bot.send_message(chat_id=message.chat.id,
                           text='Your idea was successfully saved!')


@dp.message_handler(commands=['ideas'])
async def send_ideas_request(message: types.Message):
    # if message.chat.id < 0:
    #     return
    ideas = list(select_ideas(session=session))
    if not ideas:
        await bot.send_message(chat_id=message.chat.id,
                               text='Sorry, there are no ideas for parties :(')
        return
    big_message = ''
    for idea in ideas:
        big_message += f'{idea}\n\n'
    await bot.send_message(chat_id=message.chat.id, text=big_message)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    if message.chat.id > 0:
        return
    if message.chat.id < 0:
        global GROUP_ID
        GROUP_ID = message.chat.id
    result = await bot.send_poll(
        chat_id=message.chat.id,
        question='Кем вы хотите быть?',
        options=['Суетологом! (организатором мероприятий)', 'Тусером! (участником мероприятий)'],
        is_anonymous=False
    )


@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    commands = [
        '/help',
        '/start',
        '/show_nearest',
        '/edit',
        '/edit_info <date> <description>',
        '/set_status',
        '/decline_organization',
        '/idea <description>',
        '/ideas',
        '/reset'
    ]
    descriptions = [
        'показывает список доступных команд',
        'запускает опросник о распределении ролей в группе',
        'показывает ближайшее мероприятие',
        'показывает мероприятие, которые может изменить организатор (в личке)',
        'изменяет описание мероприятия на этот день (в личке)',
        'изменяет статус роли (в личке)',
        'организатор может отказаться от организации мероприятия (в личке)',
        'записывает идею для сует (в личке)',
        'показывает записанные для сует идеи',
        'чистит базу данных'
    ]
    big_message ='Это help message\n'
    for command, description in zip(commands, descriptions):
        big_message += f'{command} - {description}\n'
    await bot.send_message(chat_id=message.chat.id, text=big_message)


@dp.message_handler(commands=['reset'])
async def process_help_command(message: types.Message):
    global session
    session = clear_session()
    await bot.send_message(chat_id=message.chat.id, text='Database is cleared!')


@dp.message_handler(commands=['send_poll'])
async def send_send_poll_request(message: types.Message):
    question = ' '.join(message.text.split()[1:])
    if not question:
        question = 'Выбираем дату суеты на следующей неделе!'
    if message.chat.id < 0:
        return
    user = session.execute(select(User).filter_by(user_id=message.from_user.id)).scalar()
    if not user:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not in group chat of SUETA')
        return
    if not user.is_organizer:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not organizer!')
        return
    parties = list(session.execute(select(Party).filter_by(organizer_id=user.user_id)).scalars())
    if not parties:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you have no planned parties')
        return
    min_datetime = min(party.date_datetime for party in parties if not party.done)
    nearest_party = session.execute(select(Party).filter_by(organizer_id=user.user_id).filter_by(date_datetime=min_datetime)).scalar()
    print(f'We are in send_poll func\n'
          f'{min_datetime, type(min_datetime)}\n'
          f'{nearest_party}')

    dates = [
        min_datetime + timedelta(days=days)
        for days in range(2, 9)
    ]

    options = [
        f'{x.strftime("%a")} {x.date()}'
        for x in dates
    ] + ['тык']

    poll = await bot.send_poll(
        chat_id=GROUP_ID,
        question=question,
        options=options,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    create_poll(poll_id=poll.poll.id, party_id=nearest_party.party_id, message_id=poll.message_id,
                session=session)
    await bot.pin_chat_message(chat_id=GROUP_ID, message_id=poll.message_id)


@dp.message_handler(commands=['show_poll'])
async def send_show_poll_results_request(message: types.Message):
    if message.chat.id < 0:
        return
    user = session.execute(select(User).filter_by(user_id=message.from_user.id)).scalar()
    if not user:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not in group chat of SUETA')
        return
    if not user.is_organizer:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not organizer!')
        return
    parties = list(session.execute(select(Party).filter_by(organizer_id=user.user_id)).scalars())
    if not parties:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you have no planned parties')
        return
    min_datetime = min(party.date_datetime for party in parties if not party.done)
    nearest_party = session.execute(select(Party).filter_by(organizer_id=user.user_id).filter_by(date_datetime=min_datetime)).scalar()

    poll = session.execute(select(Poll).filter_by(party_id=nearest_party.party_id)).scalar()

    await bot.forward_message(
        chat_id=user.user_id,
        from_chat_id=GROUP_ID,
        message_id=poll.message_id
    )


@dp.message_handler(commands=['set_date'])
async def send_set_date_request(message: types.Message):
    if message.chat.id < 0:
        return
    user = session.execute(select(User).filter_by(user_id=message.from_user.id)).scalar()
    if not user:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not in group chat of SUETA')
        return
    if not user.is_organizer:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not organizer!')
        return
    parties = list(session.execute(select(Party).filter_by(organizer_id=user.user_id)).scalars())
    if not parties:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you have no planned parties')
        return
    min_datetime = min(party.date_datetime for party in parties if not party.done)
    nearest_party = session.execute(select(Party).filter_by(organizer_id=user.user_id).filter_by(date_datetime=min_datetime)).scalar()
    print(f'We are in set_date func\n'
          f'{min_datetime, type(min_datetime)}\n'
          f'{nearest_party}')

    dates = [
        min_datetime + timedelta(days=days)
        for days in range(2, 9)
    ]

    buttons = [
        types.InlineKeyboardButton(f'{x.strftime("%a")} {x.date()}',
                                   callback_data=f'btn_set_date_{str(x.date())}')
        for x in dates
    ]
    answer_set_date = types.InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for button in buttons:
        answer_set_date.add(button)
    await bot.send_message(
        chat_id=message.chat.id,
        text='В какой день хочешь провести суюту на следующей неделе?',
        reply_markup=answer_set_date
    )


@dp.callback_query_handler(lambda c: c.data.startswith('btn_set_date_'))
async def process_callback_button_set_date(callback_query: types.CallbackQuery):
    # print(f'We are in set_date_process_callback\n'
    #       f'callback_query = {callback_query}\n'
    #       f'message = {callback_query.message}\n'
    #       f'values = {callback_query.values}\n'
    #       f'answer = {callback_query.answer}')
    user = session.execute(select(User).filter_by(user_id=callback_query.from_user.id)).scalar()
    day = callback_query.data[-10:]
    day = datetime.strptime(day, '%Y-%m-%d')

    parties = list(session.execute(select(Party).filter_by(organizer_id=user.user_id)).scalars())
    min_datetime = min(party.date_datetime for party in parties if not party.done)
    nearest_party = session.execute(
        select(Party).filter_by(organizer_id=user.user_id).filter_by(date_datetime=min_datetime)).scalar()
    nearest_party.actual_datetime = day
    session.commit()
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(user.user_id, text=f'Successfully set date:\n'
                                              f'{nearest_party}')


@dp.message_handler()
async def read_user_message(message: types.Message):
    print('GET MESSAGE')
    if message.chat.id < 0:
        return
    user = session.execute(select(User).filter_by(user_id=message.from_user.id)).scalar()
    if not user:
        await bot.send_message(chat_id=user.user_id, text='Sorry, you are not in group chat of SUETA')
        return
    if user.state == 0:
        await bot.send_message(chat_id=user.user_id, text='Firstly send me /edit')
        return
    if user.state == 1:
        party = session.execute(select(Party).filter_by(organizer_id=user.user_id)).scalar()
        party.description = message.text
        await bot.send_message(chat_id=user.user_id, text=f'Описание суеты успешно изменено:\n'
                                                          f'{party}')
    else:
        print('unknown user state')
    user.state = 0
    session.commit()


@dp.poll_answer_handler()
async def some_poll_answer_handler(poll_answer: types.PollAnswer):
    poll_ids = set(session.execute(select(Poll.poll_id)).scalars())
    if poll_answer.poll_id in poll_ids:
        poll = session.execute(select(Poll).filter_by(poll_id=poll_answer.poll_id)).scalar()
        party = session.execute(select(Party).filter_by(party_id=poll.party_id)).scalar()
        user = session.execute(select(User).filter_by(user_id=poll_answer.user.id)).scalar()
        will_visit = True
        if not poll_answer.option_ids or poll_answer.option_ids[0] == 1:
            will_visit = False
        if will_visit:
            party.users.append(user)
            # await bot.send_message(party.organizer_id, text=f'{user.username} вписался в суету!')
        else:
            if user in party.users:
                party.users.pop(party.users.index(user))
                # await bot.send_message(party.organizer_id, text=f'{user.username} выпилился из суеты!')
        session.commit()
    else:
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
    if not DEBUG and (current_time.hour < WORK_START_HOUR or current_time.hour > WORK_END_HOUR):
        return

    if DEBUG:
        print('WOKE UP')

    planned, queue, asked, answered, agree, \
    declined, count_response, last_request_time, total_declines = get_info_for_scheduler(session=session)

    if DEBUG:
        print(queue)

    next_weekends = get_next_4_weekends()[:2]  # [day1, day2, day3, day4]
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
            party = session.execute(select(Party).filter_by(date=day)).scalar()
            if party.organizer_id == -42:
                continue
            scheduler_info = session.execute(select(SchedulerInfo).filter_by(day=day, user_id=party.organizer_id)).scalar()
            last_request_time_ = scheduler_info.last_request_time
            if DEBUG:
                print(f'current_time = {current_time.timestamp()}\n'
                      f'last_request_time = {last_request_time_}\n'
                      f'{current_time.timestamp() - last_request_time_}, {MAX_RESPONSE_SECONDS_FILL_DESC}\n'
                      f'Should wait to ping = {current_time.timestamp() - last_request_time_ < MAX_RESPONSE_SECONDS_FILL_DESC}\n')
            if current_time.timestamp() - last_request_time_ < MAX_RESPONSE_SECONDS_FILL_DESC:
                continue
            if not party.description:
                scheduler_info.last_request_time = current_time.timestamp()
                session.commit()
                await bot.send_message(party.organizer_id,
                                       text=f'Please, fill in description of {day} party: type /edit')
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
                scheduler_info.is_asked = True
                scheduler_info.response_count += 1
                scheduler_info.last_request_time = current_time.timestamp()
                session.commit()
                await bot.send_message(person,
                                       text=f'Hello, can you be the organizer?\n'
                                            f'Expected date: {day}',
                                       reply_markup=answer_kb)
                return
            if not answered[day, person]:
                if scheduler_info.response_count > MAX_RESPONSE_COUNT:
                    scheduler_info.is_answered = True
                    user.is_organizer = False
                    remove_user_from_queue(user_id=person, session=session)
                    session.commit()
                elif current_time.timestamp() - last_request_time[day, person] < MAX_RESPONSE_SECONDS:
                    return
                await bot.send_message(person,
                                       text=f'Kind reminder\n'
                                            f'Could you, please, be the organizer?\n'
                                            f'Expected date: {day}',
                                       reply_markup=answer_kb)

                scheduler_info.response_count += 1
                scheduler_info.last_request_time = current_time.timestamp()
                session.commit()
                return

        if queue:
            planned[day] = True
            planned_day.is_planned = True
            session.commit()

            _ = create_party(
                title='Random', description='', location='Random', date=day,
                organizer_id=-42, cost=0, done=False, session=session
            )

            await bot.send_message(GROUP_ID,
                                   text=f'I didn\'t find organizer for expected date: {day}\n'
                                        f'So let\'s go to RANDOM PLACE!!!!!! MAXIMUM SUETI)')


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
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
