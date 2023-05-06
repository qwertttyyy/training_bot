from sqlite3 import Cursor
from datetime import datetime as dt

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    CallbackQueryHandler,
)

from bot.commands.command_list import REPORT
from bot.exceptions import ChatDataError
from config import DATABASE, TRAINER_ID, SPREADSHEET_ID
from bot.utilities import (
    get_students_ids,
    get_data_db,
    send_message,
    reply_message,
    except_function, message_logger, clean_chat_data, cancel_markup,
)
from google_sheets.sheets import GoogleSheet

START, DISTANCE, AVG_PACE, AVG_HEART_RATE, SCREENSHOT = range(5)
NUMBER_REGEX = r'^\d{1,5}([.,:]\d{1,3})?$'
DATA_KEYS = ['report', 'distance', 'avg_pace', 'avg_heart_rate']


@except_function
def send_report(update, _):
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

        return START
    reply_message(update, 'Ты тренер, тебе не нужно отправлять отчёты)')
    return ConversationHandler.END


@except_function
def get_report(update, context):
    context.chat_data[DATA_KEYS[0]] = update.message.text
    reply_message(
        update,
        'Теперь вводи данные из Strava. Они должны быть целым или '
        'дробным числом до 3-х знаков после запятой\n'
        'Расстояние (м или км):',
        cancel_markup,
    )

    return DISTANCE


@except_function
def get_distance(update, context):
    context.chat_data[DATA_KEYS[1]] = update.message.text
    reply_message(update, 'Средний темп:', cancel_markup)

    return AVG_PACE


@except_function
def get_avg_pace(update, context):
    context.chat_data[DATA_KEYS[2]] = update.message.text
    reply_message(update, 'Средний пульс:', cancel_markup)

    return AVG_HEART_RATE


@except_function
def get_avg_heart_rate(update, context):
    chat_id = update.effective_chat.id
    context.chat_data[DATA_KEYS[3]] = update.message.text

    get_name = (
        'SELECT name, last_name FROM Students WHERE chat_id = ?',
        (update.effective_chat.id,),
    )
    name = get_data_db(DATABASE, get_name, method=Cursor.fetchone)
    fullname = f'{name[0]} {name[1]}'

    report_data = []

    for key in DATA_KEYS:
        data = context.chat_data.get(key)
        if not name:
            message_logger.exception(f'Отсутствует переменная {key}')
            raise ChatDataError()
        report_data.append(data)

    message = (
        f'Отчёт после тренировки студента {fullname}\n'
        f'Дата: {dt.now().strftime("%d.%m.%Y")}\n'
        f'{report_data[0]}\n'
        f'Расстояние: {report_data[1]}\n'
        f'Средний темп: {report_data[2]}\n'
        f'Средний пульс: {report_data[3]}'
    )

    clean_chat_data(context, DATA_KEYS)

    send_message(context, TRAINER_ID, message)
    send_message(context, chat_id, message)
    gs = GoogleSheet(SPREADSHEET_ID)
    gs.send_to_table(report_data[1:], fullname, 'F')

    buttons = [
        [InlineKeyboardButton('Отправить скриншот', callback_data='screen')],
        [InlineKeyboardButton('Завершить', callback_data='end')],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    reply_message(
        update,
        'Отчёт отправлен тренеру.\n'
        'Теперь можешь отправить скриншот, либо заверши диалог',
        reply_markup,
    )


@except_function
def get_screenshot(update, context):
    send_message(context, update.effective_chat.id, 'Отправь скриншот')
    return SCREENSHOT


@except_function
def send_screenshot(update, context):
    screenshot = update.message.photo[-1]
    context.bot.send_photo(chat_id=TRAINER_ID, photo=screenshot)
    reply_message(update, 'Скриншот отправлен тренеру. Диалог завершен.')

    return ConversationHandler.END


@except_function
def finish(update, context):
    send_message(context, update.effective_chat.id, 'Диалог завершен')

    return ConversationHandler.END


@except_function
def invalid_report(update, _):
    reply_message(update, 'Отправь фото!')


@except_function
def invalid_input(update, _):
    reply_message(update, 'Некорректные данные.')


@except_function
def cancel(update, context):
    send_message(context, update.effective_chat.id, 'Отменено')
    clean_chat_data(context, DATA_KEYS)

    return ConversationHandler.END


report_handler = ConversationHandler(
    entry_points=[CommandHandler(REPORT, send_report)],
    states={
        START: [
            MessageHandler(Filters.text, get_report),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
        DISTANCE: [
            MessageHandler(Filters.regex(NUMBER_REGEX), get_distance),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
        AVG_PACE: [
            MessageHandler(Filters.regex(NUMBER_REGEX), get_avg_pace),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
        AVG_HEART_RATE: [
            MessageHandler(Filters.regex(NUMBER_REGEX), get_avg_heart_rate),
            CallbackQueryHandler(get_screenshot, pattern=r'^screen$'),
            CallbackQueryHandler(finish, pattern=r'^end$'),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
        SCREENSHOT: [
            MessageHandler(Filters.photo, send_screenshot),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_input)],
)
