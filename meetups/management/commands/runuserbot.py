import asyncio
import logging

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from django.core.management.base import BaseCommand
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from meetups.models import(
    Client,
    Event,
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
    choose_event = State()
    personal_info = State()


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message) -> None:
    client, created = await sync_to_async(Client.objects.get_or_create)(
        chat_id=message.from_user.id,
    )
    if created or not client.first_name or not client.last_name:
        await message.answer('🤖 Добро пожаловать в чат-бот\n<b>Python Meetups!</b>\n\n'
                             'Я помогу вам получить 💪 максимум от каждого события.\n'
                             'С моей помощью вы можете:\n\n'
                             '✅ быстро <b>зарегистрироваться</b> на мероприятие,\n\n'
                             '📖 легко ознакомиться с <b>программой</b>,\n\n'
                             '❓<b>задавать вопросы</b> докладчикам\n\n'
                             '💰а также поддержать нас, отправив донат.\n\n'
                             '🎫 Чтобы начать работу с ботом необходимо зарегистрироваться.',
                            parse_mode='HTML',
                            reply_markup=user_register_keyboard,
                            )
    else:
        await message.answer('Вы перешли в главное меню.',
                             parse_mode='HTML',
                             )


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'user_register', state='*')
async def user_register_handler(callback: types.CallbackQuery) -> None:
    await ClientRegisterFSM.choose_event.set()
    events = await sync_to_async(Event.objects.all)()
    inline_keyboard = []
    async for event in events:
        when_info = f'{event.date.strftime("%d.%m")} {event.start_time.strftime("%H:%M")}'
        name_info = f'{event.name}'
        event_keyboard=[[
            InlineKeyboardButton(text=name_info, callback_data=f'event_{event.id}')
        ],
        [
            InlineKeyboardButton(text=when_info, callback_data=f'event_{event.id}'),
            InlineKeyboardButton(text='✅', callback_data=f'event_choose_{event.id}'),
            InlineKeyboardButton(text='❔', callback_data=f'event_about_{event.id}'),
        ]]
        inline_keyboard += event_keyboard
    events_keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await callback.message.edit_text('Пожалуйста, выберите <b>мероприятие</b>, которое Вас интересует, нажав галочку - ✅\n\n'
                                     'Вы можете также посмотреть описание мероприятия, нажав на знак вопроса -❔',
                                     parse_mode='HTML',
                                     reply_markup=events_keyboard,
                                    )

@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('event_'),
                           state=ClientRegisterFSM.choose_event)
async def event_choose_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    event_id = callback.data.split('_')[-1]
    event = await sync_to_async(Event.objects.get)(id=event_id)
    if callback.data.startswith('event_about_'):
        event_register_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='Регистрация', callback_data=f'event_choose_{event.id}'),
                InlineKeyboardButton(text='Назад', callback_data='user_register'),
            ],
        ])
        await callback.message.edit_text(event.description,
                                         parse_mode='HTML',
                                         reply_markup=event_register_keyboard,
                                         )
    if callback.data.startswith('event_choose_'):
        async with state.proxy() as data:
            data['event'] = event

        await ClientRegisterFSM.next()
        await callback.message.answer(f'Вы выбрали мероприятие: <b>{event.name}</b>\n'
                                      'Для продолжения регистрации введите Ваше имя и '
                                      'фамилию в формате: <b>Имя Фамилия</b>',
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
    logger.info(f'first_name: {first_name}, last_name: {last_name}')
    client, _ = await sync_to_async(Client.objects.get_or_create)(chat_id=message.from_user.id)
    client.first_name = first_name
    client.last_name = last_name
    await sync_to_async(client.save)()
    await bot.send_message(client.chat_id,
                           f'{client.first_name} {client.last_name}, Вы успешно зарегистрированы!',
                           parse_mode='HTML',
                           )
    await state.finish()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        executor.start_polling(dp, skip_updates=True)
