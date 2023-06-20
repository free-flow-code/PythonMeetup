import logging

from django.core.management.base import BaseCommand
from aiogram import Bot, Dispatcher, executor, types
from conf import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
)

logger = logging.getLogger('UserBot')

bot = Bot(settings.TG_TOKEN_API)
dp = Dispatcher(bot)


@dp.message_handler()
async def echo(message: types.Message):
    if message.text.count(' ') >= 1:
        await message.answer(text=message.text.upper())


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        executor.start_polling(dp)
