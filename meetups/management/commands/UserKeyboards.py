import logging
from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async

from meetups.models import Event, Presentation, Visitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
)

logger = logging.getLogger('UserKeyboards')


def get_user_main_keyboard(client):
    inline_keyboard=[]

    today = datetime.today()
    now = datetime.now()

    current_event = Event.objects.filter(date=today, start_time__gte=now.time()).first()
    logger.info(f'current_event: {current_event}')
    current_presentation = None
    if current_event:
        current_presentation = Presentation.objects.filter(
            event=current_event,
            start_time__lte=now.time(),
            is_finished=False
        )
    logger.info(f'current_presentation: {current_presentation}')
    first_row = []
    if current_event:
        first_row.append(
            InlineKeyboardButton(text='Программа', callback_data='show_schedule'),
        )
    if current_presentation is not None:
        first_row.append(
            InlineKeyboardButton(text='Текущий доклад', callback_data='show_current_presentation'),
        )
    if first_row:
        inline_keyboard.append(first_row)

    user_presentations = await sync_to_async(Presentation.objects.all)()
    logger.info(f'user_presentations: {user_presentations}')
    if user_presentations:
        inline_keyboard.append([
            InlineKeyboardButton(text='Мои доклады', callback_data='show_my_presentations'),
        ])

    other_events = await sync_to_async(Event.objects.exclude)(date__lt=today, client=client)
    user_events = await sync_to_async(Visitor.objects.filter)(client=client)
    user_events = await sync_to_async(user_events.values_list)('event', flat=True)
    user_events = await sync_to_async(user_events.distinct)()
    events_row = []
    if user_events:
        events_row.append(
            InlineKeyboardButton(text='Мои мероприятия', callback_data='show_my_events'),
        )
    if other_events:
        events_row.append(
            InlineKeyboardButton(text='Другие мероприятия', callback_data='show_other_events'),
        )
    if events_row:
        inline_keyboard.append(events_row)

    inline_keyboard.append([
        InlineKeyboardButton(text='Сделать донат', callback_data='donate'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)