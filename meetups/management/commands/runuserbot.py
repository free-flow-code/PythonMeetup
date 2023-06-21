import logging

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from django.core.management.base import BaseCommand
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from meetups.models import(
    Client,
)
from asgiref.sync import sync_to_async
from conf import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
)

logger = logging.getLogger('UserBot')

storage = MemoryStorage()
bot = Bot(settings.TG_TOKEN_API)
dp = Dispatcher(bot=bot, storage=storage)

user_register_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='Зарегистрироваться', callback_data='user_register'),
    ],
])


class ClientRegisterFSM(StatesGroup):
    personal_info = State()


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message) -> None:
    client, _ = await sync_to_async(Client.objects.get_or_create)(
        chat_id=message.from_user.id,
    )
    await message.answer('Добро пожаловать! Чтобы начать работу с ботом необходимо зарегистрироваться.',
                         parse_mode='HTML',
                         reply_markup=user_register_keyboard,
                         )

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'user_register')
async def user_register_handler(callback: types.CallbackQuery) -> None:
    await ClientRegisterFSM.personal_info.set()
    await callback.message.edit_text('Введите ваше имя и фамилию в формате: <b>Имя Фамилия</b>',
                                     parse_mode='HTML',
                                    )


@dp.message_handler(state=ClientRegisterFSM.personal_info)
async def user_register_personal_info_handler(message: types.Message, state: FSMContext) -> None:
    if message.text.count(' ') != 1:
        await message.answer('Неверный формат ввода. Попробуйте еще раз.\n'
                             'Введите ваше имя и фамилию в формате: <b>Имя Фамилия</b>',
                             parse_mode='HTML',
                             )
        return
    first_name, last_name = message.text.split()
    client, _ = await sync_to_async(Client.objects.get_or_create)(
        chat_id=message.from_user.id,
        defaults={
            'first_name': first_name,
            'last_name': last_name,
        },
    )
    await bot.send_message(client.chat_id,
                           f'Вы успешно зарегистрированы!',
                         parse_mode='HTML',
                         )
    await state.finish()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        executor.start_polling(dp, skip_updates=True)
