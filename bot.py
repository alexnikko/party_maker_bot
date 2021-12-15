from aiogram import Bot, types, filters
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

import credentials

from sqlalchemy import select
from models.base import clear_session
from models.core import create_user, select_all_users, add_user_to_queue, delete_user
from models.user import User
from models.user_queue import UserQueue

import warnings

warnings.filterwarnings('ignore')

import logging
logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=credentials.token)
dp = Dispatcher(bot)
session = clear_session()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    result = await bot.send_poll(
        chat_id=message.chat.id,
        question='Кем вы хотите быть?',
        options=['Суетологом! (организатором мероприятий)', 'Тусером! (участником мероприятий)'],
        is_anonymous=False
    )
    print(result)


# @dp.message_handler()
# async def echo(message: types.Message):
#     await bot.send_poll(
#         chat_id=message.from_user.id,
#         question='Kaggle or party?',
#         options=['a', 'b'],
#         is_anonymous=False
#     )
# await message.reply(message.text)
@dp.poll_answer_handler()
async def some_poll_answer_handler(poll_answer: types.PollAnswer):
    print(poll_answer)
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

    print('CURRENT USER DB STATE:')
    for user in list(select_all_users(session=session)):
        print(user)

    print('CURRENT QUEUE DB STATE:')
    for user_in_queue in list(session.execute(select(UserQueue)).scalars()):
        print(user_in_queue)


@dp.message_handler()
async def create_deeplink(message: types.Message):
    print(message)
    await bot.send_message(message.chat.id, reply_to_message_id=message.message_id,
                           text=f'THANK YOU SO MUCH FOR YOU MESSAGE, DEAR {message.from_user.mention}')

# @dp.updates_handler()
# @dp.chat_member_handler()
# async def greet_chat_members(update: types.Update) -> None:
#     print(update)
#     new_member = update.chat_member.new_chat_member
#     old_member = update.chat_member.old_chat_member
#     print(new_member)
#     print(old_member)
#     await bot.send_message(new_member.user.username, text='Greetings!')
@dp.my_chat_member_handler()
async def some_handler(my_chat_member: types.ChatMemberUpdated):
    print(my_chat_member)
# @dp.chat_member_handler()
# async def some_handler(chat_member: types.ChatMemberUpdated):
#     print(chat_member)
# @dp.chat_join_request_handler()
# async def greet_chat_members(chat_member: types.ChatJoinRequest) -> None:
#     print(chat_member)
# new_member = update.chat_member.new_chat_member
# old_member = update.chat_member.old_chat_member
# print(new_member)
# print(old_member)
# await bot.send_message(new_member.user.id, text='Hello!!!!!!')

if __name__ == '__main__':
    executor.start_polling(dp)
