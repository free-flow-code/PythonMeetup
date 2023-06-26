import asyncio
from datetime import datetime
import calendar

import aiogram.utils.callback_data
from aiogram.utils.exceptions import ChatNotFound
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
'''from meetups.models import (
    Client,
    Event,
    Presentation,
    Visitor,
    Organizer
)'''
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from meetups.management.commands.runuserbot import *


class CreateEventFSM(StatesGroup):
    name = State()
    description = State()
    year = State()
    month = State()
    day = State()
    start_time = State()


class EditPresentation(StatesGroup):
    id = State()
    flag = State()
    time = State()


class CreatePresentationFSM(StatesGroup):
    event_id = State()
    name = State()
    annotation = State()
    start_time = State()
    end_time = State()
    speaker_id = State()
    speaker_name = State()



def get_events_details(events):
    events_details = []
    for event in events:
        events_details.append(
            {
                'title': f'{event}',
                'id': f'{event.id}'
            }
        )
    return events_details


def get_admin_keyboard(events_details):
    admin_keyboard = []
    for event in events_details:
        admin_keyboard.append(
            [
                InlineKeyboardButton(text=event['title'], callback_data=f'edit_program_{event["id"]}'),
            ]
        )

    admin_keyboard.append([
        InlineKeyboardButton(text='Создать мероприятие', callback_data='create_event'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=admin_keyboard)


@dp.message_handler(commands=['admin'])
async def admin_command(message: types.Message) -> None:
    try:
        organizer = await sync_to_async(Organizer.objects.get)(user_id=message.from_user.id)
    except ObjectDoesNotExist:
        await message.answer(
            'Вы не являетесь организатором',
            parse_mode='HTML'
        )
        return
    if organizer:
        organizer_events = await sync_to_async(Event.objects.filter)(organizer=organizer)
        events_details = await sync_to_async(get_events_details)(organizer_events)
        await message.answer('Вы вошли в меню для организаторов. Выберите мероприятие, чтобы изменить его программу '
                             'или создайте новое.',
                             parse_mode='HTML',
                             reply_markup=get_admin_keyboard(events_details)
                             )
    else:
        await message.answer('У вас не достаточно прав.', parse_mode='HTML')


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'create_event')
async def create_event_handler(callback: types.CallbackQuery) -> None:
    await CreateEventFSM.name.set()

    await callback.message.answer('Введите название для нового мероприятия:', parse_mode='HTML')


@dp.message_handler(state=CreateEventFSM.name)
async def get_event_description(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['name'] = message.text
    await CreateEventFSM.next()

    await message.answer('Добавьте описание:', parse_mode='HTML')


@dp.message_handler(state=CreateEventFSM.description)
async def get_event_year(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['description'] = message.text
    await CreateEventFSM.next()

    await message.answer(
        'Выберите дату для мероприятия.\nСначала выберите год:',
        parse_mode='HTML',
        reply_markup=get_year_keyboard()
    )


def get_year_keyboard():
    year = datetime.now().year
    inline_kb = InlineKeyboardMarkup(row_width=5)
    inline_kb.row()
    for year in range(year - 2, year + 3):
        inline_kb.insert(InlineKeyboardButton(str(year), callback_data=f'set_year_{year}'))

    return inline_kb


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('set_year_'),
                           state=CreateEventFSM.year)
async def get_event_month(callback: types.CallbackQuery, state: FSMContext) -> None:
    year = callback.data.split('_')[-1]
    async with state.proxy() as data:
        data['year'] = str(year)
    await CreateEventFSM.next()
    await callback.message.answer('Теперь выберите месяц:', parse_mode='HTML', reply_markup=get_month_keyboard())


def get_month_keyboard():
    months = [("Jan", '01'),
              ("Feb", '02'),
              ("Mar", '03'),
              ("Apr", '04'),
              ("May", '05'),
              ("Jun", '06'),
              ("Jul", '07'),
              ("Aug", '08'),
              ("Sep", '09'),
              ("Oct", '10'),
              ("Nov", '11'),
              ("Dec", '12')]
    inline_kb = InlineKeyboardMarkup(row_width=6)
    inline_kb.row()
    for month in months[0:6]:
        inline_kb.insert(InlineKeyboardButton(
            month[0],
            callback_data=f"set_month_{month[1]}"
        ))
    inline_kb.row()
    for month in months[6:12]:
        inline_kb.insert(InlineKeyboardButton(
            month[0],
            callback_data=f"set_month_{month[1]}"
        ))

    return inline_kb


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('set_month_'),
                           state=CreateEventFSM.month)
async def get_event_day(callback: types.CallbackQuery, state: FSMContext) -> None:
    month = callback.data.split('_')[-1]
    async with state.proxy() as data:
        data['month'] = str(month)
    await CreateEventFSM.next()

    await callback.message.answer(f'Выберите день:', parse_mode='HTML', reply_markup=get_days_keyboard(month))


def get_days_keyboard(month):
    year = datetime.now().year
    inline_kb = InlineKeyboardMarkup(row_width=7)
    inline_kb.row()
    for day in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]:
        inline_kb.insert(InlineKeyboardButton(day, callback_data=' '))

    month_calendar = calendar.monthcalendar(year, int(month))
    for week in month_calendar:
        inline_kb.row()
        for day in week:
            if (day == 0):
                inline_kb.insert(InlineKeyboardButton(" ", callback_data=' '))
                continue
            inline_kb.insert(InlineKeyboardButton(str(day), callback_data=f'set_day_{day}'))

    return inline_kb


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('set_day'), state=CreateEventFSM.day)
async def get_event_time(callback: types.CallbackQuery, state: FSMContext) -> None:
    day = callback.data.split('_')[-1]
    async with state.proxy() as data:
        data['day'] = str(day)
    await CreateEventFSM.next()

    await callback.message.answer(
        'Осталось выбрать время начала мероприятия:',
        parse_mode='HTML',
        reply_markup=get_time_keyboard()
    )


def get_time_keyboard():
    inline_kb = InlineKeyboardMarkup(row_width=4)
    inline_kb.row()
    for hour in range(0, 4):
        inline_kb.insert(InlineKeyboardButton(f'{hour}:00', callback_data=f'set_time_{hour}:00'))
    inline_kb.row()
    for hour in range(4, 8):
        inline_kb.insert(InlineKeyboardButton(f'{hour}:00', callback_data=f'set_time_{hour}:00'))
    inline_kb.row()
    for hour in range(8, 12):
        inline_kb.insert(InlineKeyboardButton(f'{hour}:00', callback_data=f'set_time_{hour}:00'))
    inline_kb.row()
    for hour in range(12, 16):
        inline_kb.insert(InlineKeyboardButton(f'{hour}:00', callback_data=f'set_time_{hour}:00'))
    inline_kb.row()
    for hour in range(16, 20):
        inline_kb.insert(InlineKeyboardButton(f'{hour}:00', callback_data=f'set_time_{hour}:00'))
    inline_kb.row()
    for hour in range(20, 24):
        inline_kb.insert(InlineKeyboardButton(f'{hour}:00', callback_data=f'set_time_{hour}:00'))

    return inline_kb


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('set_time'),
                           state=CreateEventFSM.start_time)
async def create_event(callback: types.CallbackQuery, state: FSMContext) -> None:
    time = callback.data.split('_')[-1]
    async with state.proxy() as data:
        data['start_time'] = datetime.strptime(time, '%H:%M').time()
    event_details = await state.get_data()

    date = '.'.join((event_details['day'], event_details['month'], event_details['year']))
    event, _ = await sync_to_async(Event.objects.get_or_create)(
        name=event_details['name'],
        description=event_details['description'],
        date=datetime.strptime(date, '%d.%m.%Y').date(),
        start_time=event_details['start_time']
    )
    await sync_to_async(event.save)()
    await state.finish()

    organizer = await sync_to_async(Organizer.objects.get)(user_id=callback.from_user.id)
    await sync_to_async(organizer.events.add)(event)
    await sync_to_async(organizer.save)()
    organizer_events = await sync_to_async(Event.objects.filter)(organizer=organizer)
    events_details = await sync_to_async(get_events_details)(organizer_events)

    await callback.message.answer(
        'Новое мероприятие создано!\n'
        'Выберите мероприятие, чтобы изменить его программу или создайте новое.',
        parse_mode='HTML',
        reply_markup=get_admin_keyboard(events_details)
    )


def get_presentations_keyboard(presentations, event_id):
    inline_kb = InlineKeyboardMarkup(row_width=1)
    for presentation in presentations:
        inline_kb.insert(InlineKeyboardButton(
            f'{presentation.name}',
            callback_data=f'edit_presentation_{presentation.id}'
        ))
        inline_kb.row()
    inline_kb.insert(InlineKeyboardButton('Новый доклад', callback_data=f'create_presentation_{event_id}'))

    return inline_kb


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('edit_program_'))
async def edit_event(callback: types.CallbackQuery) -> None:
    event_id = callback.data.split('_')[-1]
    event = await sync_to_async(Event.objects.get)(id=event_id)
    presentations = await sync_to_async(Presentation.objects.filter)(event=event)
    await callback.message.answer(
        'Выберите доклад, чтобы изменить время его начала и завершения, либо создайте новый.',
        parse_mode='HTML',
        reply_markup=await sync_to_async(get_presentations_keyboard)(presentations, event_id)
    )


def edit_presentation_time_keyboard():
    inline_kb = InlineKeyboardMarkup(row_width=1)
    inline_kb.insert(InlineKeyboardButton('Изменить время начала', callback_data='edit_time_start'))
    inline_kb.row()
    inline_kb.insert(InlineKeyboardButton('Изменить время завершения', callback_data='edit_time_end'))

    return inline_kb


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('edit_presentation_'))
async def edit_presentation(callback: types.CallbackQuery, state: FSMContext) -> None:
    presentation_id = callback.data.split('_')[-1]
    await EditPresentation.id.set()
    async with state.proxy() as data:
        data['id'] = presentation_id
    await EditPresentation.next()
    presentation = await sync_to_async(Presentation.objects.get)(id=presentation_id)

    await callback.message.answer(
        f'<b>Время начала:</b>\n{presentation.start_time}\n\n<b>Время завершения:</b>\n{presentation.end_time}',
        parse_mode='HTML',
        reply_markup=edit_presentation_time_keyboard()
    )


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('edit_time_'),
                           state=EditPresentation.flag)
async def get_presentation_time(callback: types.CallbackQuery, state: FSMContext) -> None:
    flag = callback.data.split('_')[-1]
    async with state.proxy() as data:
        data['flag'] = flag
    await EditPresentation.next()

    await callback.message.answer('Введите время в формате ЧЧ:ММ', parse_mode='HTML')


def get_event(presentation):
    return presentation.event


def get_ids(visitors):
    return [visitor.client.chat_id for visitor in visitors]


async def sending_to_members(ids, message):
    for user_id in ids:
        await bot.send_message(user_id, message)


@dp.message_handler(state=EditPresentation.time)
async def edit_presentation_time(message: types.Message, state: FSMContext) -> None:
    try:
        time = datetime.strptime(message.text, '%H:%M').time()
    except ValueError:
        await message.answer(
            f'Не корректное время, попробуйте еще раз. Введите время в формате ЧЧ:ММ',
            parse_mode='HTML'
        )
        return
    data = await state.get_data()
    flag = data['flag']
    presentation_id = data['id']
    presentation = await sync_to_async(Presentation.objects.get)(id=presentation_id)
    event = await sync_to_async(get_event)(presentation)
    if flag == 'start':
        presentation.start_time = time
        mess = f'Время начала доклада {presentation} на мероприятии {event} изменено на {time}.'
    else:
        presentation.end_time = time
        mess = f'Время завершения доклада {presentation} на мероприятии {event} изменено на {time}.'
    await sync_to_async(presentation.save)()

    organizer = await sync_to_async(Organizer.objects.get)(user_id=message.from_user.id)
    organizer_events = await sync_to_async(Event.objects.filter)(organizer=organizer)
    events_details = await sync_to_async(get_events_details)(organizer_events)

    visitors = await sync_to_async(Visitor.objects.filter)(event=event)
    ids = await sync_to_async(get_ids)(visitors)
    try:
        ids.remove(str(message.from_user.id))
    except ValueError:
        pass
    await sync_to_async(print)(ids)

    await message.answer(
        f'Время доклада успешно изменено.\n\n'
        'Выберите мероприятие, чтобы изменить его программу или создайте новое.',
        parse_mode='HTML',
        reply_markup=get_admin_keyboard(events_details)
    )
    await state.finish()
    await sending_to_members(ids, mess)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('create_presentation_'))
async def create_presentation_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    await CreatePresentationFSM.event_id.set()
    event_id = callback.data.split('_')[-1]
    async with state.proxy() as data:
        data['event_id'] = event_id
    await CreatePresentationFSM.next()

    await callback.message.answer('Введите название для новой презентации:', parse_mode='HTML')


@dp.message_handler(state=CreatePresentationFSM.name)
async def get_presentation_name(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['name'] = message.text
    await CreatePresentationFSM.next()

    await message.answer('Добавьте описание:', parse_mode='HTML')


@dp.message_handler(state=CreatePresentationFSM.annotation)
async def get_presentation_annotation(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['annotation'] = message.text
    await CreatePresentationFSM.next()

    await message.answer(
        'Выберите время начала доклада:',
        parse_mode='HTML',
        reply_markup=get_time_keyboard()
    )


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('set_time'),
                           state=CreatePresentationFSM.start_time)
async def get_presentation_start_time(callback: types.CallbackQuery, state: FSMContext) -> None:
    time = callback.data.split('_')[-1]
    async with state.proxy() as data:
        data['start_time'] = datetime.strptime(time, '%H:%M').time()
    await CreatePresentationFSM.next()

    await callback.message.answer(
        'Выберите время завершения доклада:',
        parse_mode='HTML',
        reply_markup=get_time_keyboard()
    )


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('set_time'),
                           state=CreatePresentationFSM.end_time)
async def get_presentation_end_time(callback: types.CallbackQuery, state: FSMContext) -> None:
    time = callback.data.split('_')[-1]
    async with state.proxy() as data:
        data['end_time'] = datetime.strptime(time, '%H:%M').time()
    await CreatePresentationFSM.next()

    await callback.message.answer(
        'Осталось выбрать, кто будет спикером доклада.\nВведите telegram id докладчика:',
        parse_mode='HTML'
    )


async def create_presentation(speaker, data):
    event = await sync_to_async(Event.objects.get)(id=data['event_id'])
    presentation, _ = await sync_to_async(Presentation.objects.get_or_create)(
        name=data['name'],
        annotation=data['annotation'],
        event=event,
        start_time=data['start_time'],
        end_time=data['end_time'],
        speaker=speaker
    )
    await sync_to_async(presentation.save)()
    ids = [speaker.chat_id]
    message = f'Вы назначены спикером с докладом {data["name"]} на мероприятии {presentation.event.name}\n'\
              f'Время начала доклада {data["start_time"]}'
    try:
        await sending_to_members(ids, message)
    except ChatNotFound:
        pass


@dp.message_handler(state=CreatePresentationFSM.speaker_id)
async def get_presentation_speaker(message: types.Message, state: FSMContext) -> None:
    speaker_id = message.text
    async with state.proxy() as data:
        data['speaker_id'] = speaker_id

    try:
        speaker = await sync_to_async(Client.objects.get)(chat_id=speaker_id)
        data = await state.get_data()
        await create_presentation(speaker, data)
        await state.finish()

        organizer = await sync_to_async(Organizer.objects.get)(user_id=message.from_user.id)
        organizer_events = await sync_to_async(Event.objects.filter)(organizer=organizer)
        events_details = await sync_to_async(get_events_details)(organizer_events)

        await message.answer(
            'Новый доклад создан.\nСпикер получит соответствующее оповещение.'
            'Выберите мероприятие, чтобы изменить его программу или создайте новое.',
            parse_mode='HTML',
            reply_markup=get_admin_keyboard(events_details)
        )
    except ObjectDoesNotExist:
        await message.answer(
            'Этот человек еще не зарегистрирован в боте.\nЧтобы зарегистрировать введите его имя и '
            'фамилию в формате: <b>Имя Фамилия</b>',
            parse_mode='HTML'
        )
        await CreatePresentationFSM.next()


@dp.message_handler(state=CreatePresentationFSM.speaker_name)
async def create_new_speaker(message: types.Message, state: FSMContext) -> None:
    if message.text.count(' ') != 1:
        await message.answer('Неверный формат ввода. Попробуйте еще раз.\n'
                             'Введите имя и фамилию спикера в формате: <b>Имя Фамилия</b>',
                             parse_mode='HTML',
                             )
        return
    data = await state.get_data()
    first_name, last_name = message.text.split()
    client, _ = await sync_to_async(Client.objects.get_or_create)(chat_id=data['speaker_id'])
    client.first_name = first_name
    client.last_name = last_name
    await sync_to_async(client.save)()
    await create_presentation(client, data)
    await state.finish()

    organizer = await sync_to_async(Organizer.objects.get)(user_id=message.from_user.id)
    organizer_events = await sync_to_async(Event.objects.filter)(organizer=organizer)
    events_details = await sync_to_async(get_events_details)(organizer_events)

    await message.answer(
        'Новый спикер зарегистрирован и доклад создан.\nСпикер получит соответствующее оповещение.\n'
        'Выберите мероприятие, чтобы изменить его программу или создайте новое.',
        parse_mode='HTML',
        reply_markup=get_admin_keyboard(events_details)
    )
