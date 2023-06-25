from conf.wsgi import *
import logging
from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async

from meetups.models import Event, Presentation, Visitor, Client, Question, Likes

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
)

logger = logging.getLogger('UserKeyboards')


async def get_cancel_keyboard():
    inline_keyboard = [
        [
            InlineKeyboardButton(text='Отменить', callback_data='cancel'),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_just_main_menu_keyboard():
    inline_keyboard = [
        [
            InlineKeyboardButton(text='Главное меню', callback_data='main_menu'),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


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
    user_events_ids = await sync_to_async(
        Client.objects.filter(pk=client.pk,events__date__gte=today).distinct().values_list)('events', flat=True)
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


async def get_event_schedule_keyboard(event):
    presentations = await sync_to_async(Presentation.objects.filter(event=event).select_related)('speaker')
    inline_keyboard = []
    async for presentation in presentations:
        when_info = f'{presentation.start_time.strftime("%H:%M")} - {presentation.end_time.strftime("%H:%M")}'
        speaker_info = f'{presentation.speaker.first_name} {presentation.speaker.last_name}'
        name_info = f'{presentation.name}'
        presentation_keyboard = [
            [
                InlineKeyboardButton(text=speaker_info, callback_data='none'),
                InlineKeyboardButton(text=when_info, callback_data='none'),
            ],
            [
                InlineKeyboardButton(text=name_info, callback_data=f'presentation_annotation_{presentation.pk}')
            ],
            [
                InlineKeyboardButton(text='Главное меню', callback_data='main_menu'),
            ],
        ]
        inline_keyboard += presentation_keyboard
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_my_presentations_keyboard(client):
    presentations = await sync_to_async(
        Presentation.objects.filter(speaker__chat_id=client.chat_id).select_related('event').select_related
    )('speaker')
    inline_keyboard = []
    async for presentation in presentations:
        time_info = f'{presentation.start_time.strftime("%H:%M")} - {presentation.end_time.strftime("%H:%M")}'
        date_info = f'{presentation.event.date.strftime("%d.%m.%Y")}'
        name_info = f'{presentation.name}'
        presentation_keyboard = [
            [
                InlineKeyboardButton(text=date_info, callback_data='none'),
                InlineKeyboardButton(text=time_info, callback_data='none'),
            ],
            [
                InlineKeyboardButton(text=name_info, callback_data=f'none')
            ],
            [
                InlineKeyboardButton(text='Главное меню', callback_data='main_menu'),
            ],
        ]
        inline_keyboard += presentation_keyboard
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_current_presentation_keyboard(presentation, speaker):
    questions_count = await sync_to_async(presentation.questions.filter(presentation=presentation).count)()
    inline_keyboard = []
    if questions_count:
        ask_keyboard = [
            [
                InlineKeyboardButton(
                    text=f'Посмотреть вопросы (всего: {questions_count})',
                    callback_data=f'questions_show_{presentation.pk}'),
            ],
        ]
        inline_keyboard += ask_keyboard

    if speaker:
        speaker_keyboard = [
            [
                InlineKeyboardButton(text='Завершить доклад', callback_data=f'presentation_finish_{presentation.pk}'),

            ],
        ]
        inline_keyboard += speaker_keyboard
    else:
        ask_keyboard = [
            [
                InlineKeyboardButton(text='Задать вопрос', callback_data=f'question_ask_{presentation.pk}'),
            ],
        ]
        inline_keyboard += ask_keyboard
    main_menu_keyboard = [
        [
            InlineKeyboardButton(text='Главное меню', callback_data=f'main_menu'),
        ],
    ]
    inline_keyboard += main_menu_keyboard
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_current_presentation_question_keyboard(question, chat_id, speaker):
    question = question
    logger.info(f'question: {question}')
    exists_user_like = await sync_to_async(Likes.objects.filter(
        client__chat_id=chat_id,
        question=question,
    ).exists)()
    inline_keyboard = []
    author = int(question.client.chat_id) == int(chat_id)
    if speaker:
        inline_keyboard.append([
            InlineKeyboardButton(text='Закрыть вопрос', callback_data=f'question_close_{question.pk}'),
            InlineKeyboardButton(text='Контакты', callback_data=f'question_contacts_{question.pk}'),
        ])
    elif author:
        inline_keyboard.append([
            # InlineKeyboardButton(text='🔥 Вы автор данного вопроса', callback_data='none'),
        ])
    else:
        logger.info(f'exists_like - {exists_user_like}')
        if exists_user_like:
            inline_keyboard.append([
                # InlineKeyboardButton(text='✅ Вы уже поддержали данный вопрос', callback_data='none'),
            ])
        else:
            inline_keyboard.append([
                InlineKeyboardButton(text='👍 Поддержать вопрос', callback_data=f'question_like_{question.pk}'),
            ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard, row_width=2)


async def get_question_main_menu_keyboard(presentation_id, speaker):
    if speaker:
        inline_keyboard = [
            [
                InlineKeyboardButton(text='Обновить список вопросов', callback_data=f'questions_show_{presentation_id}'),
            ],
            [
                InlineKeyboardButton(text='Завершить доклад', callback_data=f'presentation_finish_{presentation_id}'),
            ],
            [
                InlineKeyboardButton(text='Главное меню', callback_data=f'main_menu'),
            ],
        ]
    else:
        inline_keyboard = [
            [
                InlineKeyboardButton(text='Задать свой вопрос', callback_data=f'question_ask_{presentation_id}'),
            ],
            [
                InlineKeyboardButton(text='Главное меню', callback_data=f'main_menu'),
            ],
        ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_presentation_annotation_keyboard():
    inline_keyboard = [
        [
            InlineKeyboardButton(text='Программа', callback_data='show_schedule'),
        ],
        [
            InlineKeyboardButton(text='Главное меню', callback_data='main_menu'),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_show_my_events_keyboard():
    inline_keyboard = [
        [
            InlineKeyboardButton(text='Мои мероприятия', callback_data='show_my_events'),
        ],
        [
            InlineKeyboardButton(text='Главное меню', callback_data='main_menu'),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_question_contacts_keyboard(presentation):
    inline_keyboard = [
        [
            InlineKeyboardButton(text='К списку вопросов', callback_data=f'questions_show_{presentation.pk}'),
        ],
        [
            InlineKeyboardButton(text='Главное меню', callback_data='main_menu'),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


async def get_donate_keyboard():
    inline_keyboard = [
        [
            InlineKeyboardButton(text='100', callback_data='pay_100'),
            InlineKeyboardButton(text='250', callback_data='pay_250'),
            InlineKeyboardButton(text='350', callback_data='pay_350'),
        ],
        [
            InlineKeyboardButton(text='500', callback_data='pay_500'),
            InlineKeyboardButton(text='750', callback_data='pay_750'),
            InlineKeyboardButton(text='1000', callback_data='pay_1000'),
        ],
        [
            InlineKeyboardButton(text='Главное меню', callback_data='main_menu'),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


if __name__ == '__main__':
    today = datetime.today()
    presentations = Presentation.objects.filter(event=1)
    print(presentations)
