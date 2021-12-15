from aiogram import Bot, types, filters
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

import credentials

bot = Bot(token=credentials.token)
dp = Dispatcher(bot)


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
    print(poll_answer)


if __name__ == '__main__':
    executor.start_polling(dp)
