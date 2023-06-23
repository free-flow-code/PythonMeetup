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
from meetups.management.commands.user_keyboards import (
    get_user_main_keyboard,
    get_event_schedule_keyboard,
    get_current_presentation_keyboard,
    get_current_presentation_question_keyboard,
    get_question_main_menu_keyboard,
)

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
                             'Если вы выступаете на мероприятии, то вы также сможете '
                             '👀 посмотреть вопросы от зрителей вашей презентации\n\n'
                             '🎫 Чтобы начать работу с ботом необходимо зарегистрироваться.',
                            parse_mode='HTML',
                            reply_markup=user_register_keyboard,
                            )
    else:
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


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'show_schedule', state='*')
async def show_schedule_handler(callback: types.CallbackQuery) -> None:
    today = datetime.today()
    now = datetime.now()
    current_event = await sync_to_async(Event.objects.filter(date=today, start_time__lte=now.time()).first)()
    await callback.message.answer(f'<b>{current_event.name}</b>\n\n'
                                  f'<em>Нажмите на название доклада, чтобы '
                                  f'📖 прочитать о нем подробнее или '
                                  f'🙋‍♂️задать вопрос докладчику.</em>\n\n'
                                  f'🕓 РАСПИСАНИЕ НА СЕГОДНЯ:',
                                  parse_mode='HTML',
                                  reply_markup=await get_event_schedule_keyboard(current_event),
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


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'show_current_presentation', state='*')
async def show_current_presentation_handler(callback: types.CallbackQuery) -> None:
    today = datetime.today()
    now = datetime.now()
    current_event = await sync_to_async(Event.objects.filter(date=today, start_time__lte=now.time()).first)()
    if current_event:
        current_presentation = await sync_to_async(Presentation.objects.filter(
            event=current_event,
            start_time__lte=now.time(),
            is_finished=False,
        ).select_related('speaker').first)()
    speaker_chat_id = current_presentation.speaker.chat_id
    speaker = int(speaker_chat_id) == int(callback.from_user.id)
    logger.info(f'speaker: {speaker}')
    texts = {
        'True': f'CЕЙЧАС ИДЕТ ВАШ ДОКЛАД:\n\n'
               f'<b>{current_presentation.name}</b>\n\n'
               f'<b>Докладчик</b>\n'
               f'{current_presentation.speaker.first_name} {current_presentation.speaker.last_name}\n\n'
               f'<em>Здесь вы можете посмотреть вопросы'
               f' или завершить доклад</em>',
        'False': f'CЕЙЧАС ИДЕТ ДОКЛАД:\n\n'
               f'<b>{current_presentation.name}</b>\n\n'
               f'<b>Описание:</b>\n'
               f'{current_presentation.annotation}\n\n'
               f'<b>Докладчик</b>\n'
               f'{current_presentation.speaker.first_name} {current_presentation.speaker.last_name}\n\n'\
               f'<em>Здесь вы можете задать вопрос докладчику'
               f' или посмотреть заданные ранее вопросы и'
               f'  поддержать интересные вам, нажав на 👍</em>\n\n'
    }
    await callback.message.answer(texts[str(speaker)],
                                  parse_mode='HTML',
                                  reply_markup=await get_current_presentation_keyboard(
                                      current_presentation,
                                      speaker,
                                  ),
                                  )

@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('questions_show'), state='*')
async def show_current_presentation_questions_handler(callback: types.CallbackQuery) -> None:
    presentation_id = callback.data.split('_')[-1]
    questions = await sync_to_async(
        Question.objects.filter(
            presentation=presentation_id,
        ).all().select_related('presentation').select_related('client').prefetch_related)('likes')
    presentation = await sync_to_async(
        Presentation.objects.filter(pk=presentation_id).select_related('speaker').first
    )()
    speaker_chat_id = presentation.speaker.chat_id
    speaker = int(speaker_chat_id) == int(callback.from_user.id)
    async for question in questions:
        likes_count = await sync_to_async(question.likes.count)()
        await callback.message.answer(f'<b>{question.presentation.name}:</b>\n\n'
                                      f'{question.text}\n\n'
                                      f'👍 <em>{likes_count}</em>',
                                      parse_mode='HTML',
                                      reply_markup=await get_current_presentation_question_keyboard(
                                        question,
                                        callback.from_user.id,
                                        speaker,
                                      ),
                                    )
    texts = {
        'True': f'Не забывайте иногда <b>обновлять список вопросов</b>, чтобы не пропустить новые!',
        'False': f'gfg Вы также можете задать свой вопрос или вернуться в главное меню:'
    }
    await callback.message.answer(texts[str(speaker)],
                                  parse_mode='HTML',
                                  reply_markup=await get_question_main_menu_keyboard(
                                      presentation_id,
                                      speaker,
                                  ),
                                  )


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        executor.start_polling(dp, skip_updates=True)
