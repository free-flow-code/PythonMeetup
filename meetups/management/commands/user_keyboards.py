from conf.wsgi import *
import logging
from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async

from meetups.models import Event, Presentation, Visitor, Client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
)

logger = logging.getLogger('UserKeyboards')


async def get_user_main_keyboard(client):
    inline_keyboard=[]

    today = datetime.today()
    now = datetime.now()

    current_event = await sync_to_async(Event.objects.filter(date=today, start_time__lte=now.time()).first)()
    logger.info(f'current_event: {current_event}')
    exists_current_presentation = False
    if current_event:
        exists_current_presentation = await sync_to_async(Presentation.objects.filter(
            event=current_event,
            start_time__lte=now.time(),
            is_finished=False,
        ).exists)()
    logger.info(f'current_presentation: {exists_current_presentation}')
    first_row = []
    if current_event:
        first_row.append(
            InlineKeyboardButton(text='Программа', callback_data='show_schedule'),
        )
    if exists_current_presentation:
        first_row.append(
            InlineKeyboardButton(text='Текущий доклад', callback_data='show_current_presentation'),
        )
    if first_row:
        inline_keyboard.append(first_row)

    exist_user_presentations = await sync_to_async(Presentation.objects.filter(speaker=client).exists)()
    logger.info(f'user_presentations: {exist_user_presentations}')
    if exist_user_presentations:
        inline_keyboard.append([
            InlineKeyboardButton(text='Мои доклады', callback_data='show_my_presentations'),
        ])
    user_events_ids = await sync_to_async(Client.objects.filter(pk=18, events__date__gte=today).distinct().values_list)('events', flat=True)
    user_events_ids = await sync_to_async(list)(user_events_ids)
    exist_other_events = await sync_to_async(Event.objects.exclude(pk__in=user_events_ids).exists)()
    events_row = []
    if user_events_ids:
        events_row.append(
            InlineKeyboardButton(text='Мои мероприятия', callback_data='show_my_events'),
        )
    if exist_other_events:
        events_row.append(
            InlineKeyboardButton(text='Другие мероприятия', callback_data='show_other_events'),
        )
    if events_row:
        inline_keyboard.append(events_row)

    inline_keyboard.append([
        InlineKeyboardButton(text='Сделать донат', callback_data='donate'),
        InlineKeyboardButton(text='О боте', callback_data='about'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


# async def get_event_schedule_keyboard(event):
#     presentations = await sync_to_async(Event.presentations.all)()
#     inline_keyboard = []
#     async for event in events:
#         when_info = f'{event.date.strftime("%d.%m")} {event.start_time.strftime("%H:%M")}'
#         name_info = f'{event.name}'
#         event_keyboard = [[
#             InlineKeyboardButton(text=name_info, callback_data=f'event_{event.id}')
#         ],
#             [
#                 InlineKeyboardButton(text=when_info, callback_data=f'event_{event.id}'),
#                 InlineKeyboardButton(text='✅', callback_data=f'event_choose_{event.id}'),
#                 InlineKeyboardButton(text='❔', callback_data=f'event_about_{event.id}'),
#             ]]
#         inline_keyboard += event_keyboard
#     events_keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)







if __name__ == '__main__':
    today = datetime.today()
    user_events = Client.objects.filter(pk=18, events__date__gte=today).distinct().values_list('events', flat=True)
    exist_other_events = Event.objects.exclude(pk__in=user_events)
    print(exist_other_events)
    print(user_events)
