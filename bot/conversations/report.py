from datetime import datetime as dt
from http import HTTPStatus

from psycopg2._psycopg import cursor
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from bot.commands.command_list import REPORT_COMMAND
from bot.config import DATABASE, SPREADSHEET_ID, STRAVA_ACTIVITIES, TRAINER_ID
from bot.exceptions import ChatDataError
from bot.google_sheets.sheets import GoogleSheet
from bot.utilities import (
    calculate_pace,
    cancel_button,
    cancel_markup,
    catch_exception,
    clean_chat_data,
    db_execute,
    get_access_data,
    get_data_db,
    get_students_ids,
    message_logger,
    reply_message,
    send_message,
    strava_api_request,
)

REPORT, SCREENSHOT, STRAVA, DISTANCE, AVG_TEMP, AVG_HEART_RATE = range(6)
NUMBER_REGEX = r'^\d{1,2}([.,]\d{1,2})?$'
DATA_KEYS = ['distance', 'avg_pace', 'avg_heart_rate', 'report', 'screenshots']


@catch_exception
def send_report(update, context):
    students_ids = get_students_ids(DATABASE)
    chat_id = update.effective_chat.id

    if update.effective_chat.id != TRAINER_ID:
        if chat_id not in students_ids:
            reply_message(update, 'Ты не зарегистрирован, пройди регистрацию!')

            return ConversationHandler.END

        reply_message(
            update,
            'Отправь отчёт после тренировки.\nВведи отчёт: (текст)',
            cancel_markup,
        )
        context.chat_data['screenshots'] = []
        return REPORT
    reply_message(update, 'Ты тренер, тебе не нужно отправлять отчёты)')
    return ConversationHandler.END


@catch_exception
def get_report(update, context):
    report = update.message.text
    if report.startswith('/') and not report.startswith('//'):
        invalid_input(update, context)
        return REPORT
    else:
        context.chat_data['report'] = update.message.text

        buttons = [
            [
                InlineKeyboardButton(
                    'Прикрепить скриншот', callback_data='screen'
                )
            ],
            [InlineKeyboardButton('Продолжить', callback_data='strava')],
            cancel_button,
        ]

        reply_markup = InlineKeyboardMarkup(buttons)

        reply_message(
            update,
            'Теперь можешь отправить один или несколько скриншотов по очереди,'
            ' либо можешь отправить данные из Strava',
            reply_markup,
        )


@catch_exception
def get_screenshot(update, context):
    send_message(
        context,
        update.effective_chat.id,
        'Отправь один скриншот, он будет сохранён',
    )
    return SCREENSHOT


@catch_exception
def save_screenshot(update, context):
    screenshot = InputMediaPhoto(update.message.photo[-1])
    context.chat_data['screenshots'].append(screenshot)
    buttons = [
        [
            InlineKeyboardButton(
                'Добавить ещё скриншот', callback_data='screen'
            )
        ],
        [InlineKeyboardButton('Продолжить', callback_data='strava')],
        cancel_button,
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    reply_message(
        update,
        'Скриншот сохранён.\n'
        'Можешь добавить ещё один, либо нажми продолжить, '
        'чтобы отправить данные из Strava',
        reply_markup,
    )

    return SCREENSHOT


def strava_choice(update, context):
    buttons = [
        [
            InlineKeyboardButton(
                'Ввести данные вручную', callback_data='strava_input'
            )
        ],
        [
            InlineKeyboardButton(
                'Отправить из приложения Strava', callback_data='strava_app'
            )
        ],
        cancel_button,
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    chat_id = update.effective_chat.id
    access_data = get_access_data(DATABASE, chat_id)

    message = (
        'Теперь ты можешь отправить данные из Strava с помощью ручного ввода, '
        'либо отправить данные из приложения, для этого тебе нужно '
        'авторизоваться с помощью команды /strava'
    )

    if access_data:
        message = (
            'Теперь ты можешь отправить данные из Strava с помощью ручного '
            'ввода, либо отправить данные из приложения'
        )

    send_message(
        context,
        update.effective_chat.id,
        message,
        reply_markup,
    )

    return STRAVA


@catch_exception
def get_strava_input(update, context):
    chat_id = update.effective_chat.id
    send_message(
        context,
        chat_id,
        'Теперь вводи данные из Strava в указанном формате.\n'
        'Расстояние:\n'
        '(формат 00.00 км)',
        cancel_markup,
    )
    return DISTANCE


@catch_exception
def get_distance(update, context):
    context.chat_data['distance'] = update.message.text
    reply_message(update, 'Средний темп:\n' '(формат 0:00)', cancel_markup)

    return AVG_TEMP


@catch_exception
def get_avg_pace(update, context):
    context.chat_data['avg_pace'] = update.message.text
    reply_message(update, 'Средний пульс:\n' '(формат 111)', cancel_markup)

    return AVG_HEART_RATE


@catch_exception
def get_avg_heart_rate(update, context):
    context.chat_data['avg_heart_rate'] = update.message.text
    send_strava_data(update, context)
    return ConversationHandler.END


@catch_exception
def bad_request_message(context, chat_id):
    send_message(
        context,
        chat_id,
        'Произошла ошибка получения данных из Strava, '
        'попробуй ввести данные вручную ',
    )
    return ConversationHandler.END


@catch_exception
def get_strava_app(update, context):
    chat_id = update.effective_chat.id

    access_data = get_access_data(DATABASE, chat_id)

    if access_data == HTTPStatus.BAD_REQUEST:
        bad_request_message(context, chat_id)

    elif access_data is None:
        send_message(
            context,
            chat_id,
            'Сначала авторизуйся через Strava с помощью команды /strava',
        )
        return ConversationHandler.END
    else:
        access_token = access_data['access_token']
        strava_data = strava_api_request(STRAVA_ACTIVITIES, access_token)
        if strava_data == HTTPStatus.BAD_REQUEST:
            bad_request_message(context, chat_id)
        else:
            last_run = None
            for activity in strava_data:
                if activity['type'] == 'Run':
                    last_run = activity
                    break
            if not last_run:
                send_message(context, chat_id, 'Нужные тренировки отсутствуют')
                return ConversationHandler.END
            params = ('distance', 'average_heartrate', 'elapsed_time')
            for param in params:
                value = last_run.get(param)
                if not value:
                    send_message(
                        context,
                        chat_id,
                        'Ошибка получение одного из параметров. '
                        'Попробуй ввести данные вручную',
                    )
                    return STRAVA
            distance = last_run['distance']
            avg_heart_rate = last_run['average_heartrate']
            elapsed_time = last_run['elapsed_time']
            avg_pace = calculate_pace(elapsed_time, distance)
            context.chat_data['distance'] = round(distance / 1000, 2)
            context.chat_data['avg_heart_rate'] = round(avg_heart_rate)
            context.chat_data['avg_pace'] = str(avg_pace).replace('.', ':')
            send_strava_data(update, context)
            return ConversationHandler.END


@catch_exception
def send_strava_data(update, context):
    chat_id = update.effective_chat.id

    get_name = (
        'SELECT name, last_name FROM Students WHERE chat_id = %s',
        (update.effective_chat.id,),
    )
    name = get_data_db(DATABASE, get_name, method=cursor.fetchone)
    fullname = f'{name[0]} {name[1]}'

    report_data = {}
    for key in DATA_KEYS[:-1]:
        data = context.chat_data.get(key)
        if not data:
            message_logger.exception(f'Отсутствует переменная {key}')
            raise ChatDataError()
        report_data[key] = data

    message = (
        f'Отчёт после тренировки студента {fullname}\n'
        f'Дата: {dt.now().strftime("%d.%m.%Y")}\n'
        f'"{report_data["report"]}"\n'
        f'Расстояние: {report_data["distance"]}\n'
        f'Средний темп: {report_data["avg_pace"]}\n'
        f'Средний пульс: {report_data["avg_heart_rate"]}'
    )

    send_message(context, TRAINER_ID, message)

    screenshots = context.chat_data.get('screenshots')
    if screenshots:
        context.bot.send_media_group(chat_id=TRAINER_ID, media=screenshots)

    clean_chat_data(context, DATA_KEYS)

    data_to_table = [report_data[key] for key in DATA_KEYS[:4]]

    gs = GoogleSheet(SPREADSHEET_ID)
    gs.send_to_table(data_to_table, fullname, 'F')

    db_execute(
        DATABASE,
        (
            'UPDATE students SET is_send_evening = 1 WHERE chat_id = %s',
            (chat_id,),
        ),
    )

    send_message(context, chat_id, 'Отчёт отправлен тренеру!')

    send_message(context, chat_id, message)
    if screenshots:
        context.bot.send_media_group(chat_id=chat_id, media=screenshots)

    return ConversationHandler.END


@catch_exception
def finish(update, context):
    send_message(context, update.effective_chat.id, 'Диалог завершен')

    return ConversationHandler.END


@catch_exception
def invalid_report(update, _):
    reply_message(update, 'Отправь фото!')


@catch_exception
def invalid_input(update, _):
    reply_message(update, 'Некорректные данные.')


@catch_exception
def cancel(update, context):
    send_message(context, update.effective_chat.id, 'Отменено')
    clean_chat_data(context, DATA_KEYS)

    return ConversationHandler.END


report_handler = ConversationHandler(
    entry_points=[CommandHandler(REPORT_COMMAND, send_report)],
    states={
        REPORT: [
            MessageHandler(Filters.text, get_report),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
            CallbackQueryHandler(strava_choice, pattern=r'^strava$'),
            CallbackQueryHandler(get_screenshot, pattern=r'^screen$'),
        ],
        SCREENSHOT: [
            MessageHandler(Filters.photo, save_screenshot),
            CallbackQueryHandler(get_screenshot, pattern=r'^screen$'),
            CallbackQueryHandler(strava_choice, pattern=r'^strava$'),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
        ],
        STRAVA: [
            CallbackQueryHandler(get_strava_input, pattern=r'^strava_input$'),
            CallbackQueryHandler(get_strava_app, pattern=r'^strava_app$'),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
        ],
        DISTANCE: [
            MessageHandler(Filters.regex(NUMBER_REGEX), get_distance),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
        ],
        AVG_TEMP: [
            MessageHandler(Filters.regex(r'^\d:\d{2}$'), get_avg_pace),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
        ],
        AVG_HEART_RATE: [
            MessageHandler(Filters.regex(r'^\d{2,3}$'), get_avg_heart_rate),
            CallbackQueryHandler(finish, pattern=r'^end$'),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_input)],
)
