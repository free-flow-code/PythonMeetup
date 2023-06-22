import asyncio
import logging
from datetime import datetime

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from django.core.management.base import BaseCommand
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from meetups.models import (
    Client,
    Event,
    Presentation,
    Question,
    Visitor,
)
from asgiref.sync import sync_to_async
from conf import settings
from meetups.management.commands.database import db_start, get_user_presentations, get_user_events
from meetups.management.commands.user_keyboards import get_user_main_keyboard

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


speaker_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='Мои презентации', callback_data='my_presentations'),
    ],
])

async def on_startup(dp):
    await db_start()


class ClientRegisterFSM(StatesGroup):
    choose_event = State()
    personal_info = State()


# async def is_speaker(user_id):
#     presentations = await sync_to_async(Presentation.objects.all)()
#     speakers = []
#     async for presentation in presentations:
#         speaker_id = await sync_to_async(lambda: presentation.speaker.chat_id)()
#         await sync_to_async(speakers.append)(speaker_id)
#     if str(user_id) in speakers:
#         return True


# async def get_user_main_keyboard(client):
#     inline_keyboard = []
#
#     today = datetime.today()
#     now = datetime.now()
#     current_event = await sync_to_async(Event.objects.filter(date__gte=today).first)()
#
#
#     if current_event:
#         first_row = [
#             InlineKeyboardButton(text='Программа', callback_data='show_schedule'),
#         ]
#         inline_keyboard.append(first_row)
#
#     inline_keyboard.append([
#         InlineKeyboardButton(text='Сделать донат', callback_data='donate'),
#     ])
#     return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message) -> None:
    client, created = await sync_to_async(Client.objects.get_or_create)(
        chat_id=message.from_user.id,
    )
    # if await is_speaker(message.from_user.id):
    #     await message.answer('🤖 Добро пожаловать в чат-бот\n<b>Python Meetups!</b>\n\n'
    #                          'Так как вы являетесь докладчиком на некоторых меропрятиях,'
    #                          ' то вы можете:\n\n'
    #                          '👀 посмотреть вопросы от зрителей вашей презентации,\n\n'
    #                          '✅ быстро <b>зарегистрироваться</b> на мероприятие,\n\n'
    #                          '📖 легко ознакомиться с <b>программой</b>,\n\n'
    #                          '❓<b>задавать вопросы</b> другим докладчикам\n\n'
    #                          '💰а также поддержать нас, отправив донат.\n\n'
    #                          ,
    #                          parse_mode='HTML',
    #                          reply_markup=speaker_keyboard,
    #                          )
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
        # await get_user_presentations(client.pk)
        # await get_user_events(client.pk)
        user_main_keyboard = await get_user_main_keyboard(client)
        await message.answer('Вы перешли в главное меню.',
                             parse_mode='HTML',
                             reply_markup=user_main_keyboard,
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
    async with state.proxy() as data:
        event = data['event']
    await sync_to_async(Visitor.objects.get_or_create)(
        client=client,
        event=event,
    )
    await bot.send_message(client.chat_id,
                           f'{client.first_name} {client.last_name}, Вы успешно зарегистрированы!',
                           parse_mode='HTML',
                           )
    await state.finish()


def display_presentations(presentations):
    if presentations:
        my_presentations_keyboard = []
        presentations_details = []
        number = 1
        for presentation in presentations:
            presentation_button = [
                    InlineKeyboardButton(
                        text=f'{number}',
                        callback_data=f'questions_{presentation.id}'),
                ]
            my_presentations_keyboard.append(presentation_button)
            presentations_details.append(
                f'<b>{number}.</b>\n'
                f'<b>Название:</b>\n {presentation.name}\n'
                f'<b>Мероприятие:</b>\n {presentation.event}\n'
            )
            number += 1
        presentations_details.append(
            'Нажмите на кнопку с соответствующим номером презентации, чтобы посмотреть вопросы к ней.'
        )

        return my_presentations_keyboard, presentations_details


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'my_presentations')
async def my_presentations_handler(callback: types.CallbackQuery) -> None:
    user_id = callback.from_user.id
    speaker = await sync_to_async(Client.objects.get)(chat_id=user_id)
    speaker_presentations = await sync_to_async(Presentation.objects.filter)(speaker_id=speaker.id)
    my_presentations_keyboard, presentations_details = await sync_to_async(display_presentations)(speaker_presentations)
    presentations_keyboard = InlineKeyboardMarkup(inline_keyboard=my_presentations_keyboard)

    await callback.message.edit_text('\n'.join(presentations_details),
                                     parse_mode='HTML',
                                     reply_markup=presentations_keyboard,
                                     )


def get_questions_details(questions):
    questions_details = []
    for question in questions:
        questions_details.append(
            f'<b>Вопрос от:</b>\n{str(question.client).split(": ")[-1]}\n'
            f'<b>Текст:</b>\n{question.text}'
        )
    return questions_details



@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('questions_'))
async def my_presentations_handler(callback: types.CallbackQuery) -> None:
    presentation_id = callback.data.split('_')[-1]
    presentation = await sync_to_async(Presentation.objects.get)(id=presentation_id)
    questions = await sync_to_async(Question.objects.filter)(presentation=presentation_id)
    questions_details = await sync_to_async(get_questions_details)(questions)
    await callback.message.edit_text('\n'.join(questions_details),
                                     parse_mode='HTML',
                                     )


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
