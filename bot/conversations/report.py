from sqlite3 import Cursor

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    CallbackQueryHandler,
)

from bot.commands.command_list import REPORT
from config import DATABASE, TRAINER_ID, SPREADSHEET_ID
from bot.utilities import (
    get_students_ids,
    get_data_db,
    db_execute,
    send_message,
    reply_message,
    except_function,
)
from google_sheets.sheets import GoogleSheet

START, DISTANCE, AVG_PACE, AVG_HEART_RATE, SCREENSHOT = range(5)
NUMBER_REGEX = r'^\d{1,5}(\.\d{1,3})?$'


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
        )

        return START
    reply_message(update, 'Ты тренер, тебе не нужно отправлять отчёты)')
    return ConversationHandler.END


@except_function
def get_report(update, _):
    execution = (
        'UPDATE Reports SET report = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)
    reply_message(
        update,
        'Теперь вводи данные из Strava. Они должны быть целым или '
        'дробным числом до 3-х знаков после запятой\n'
        'Расстояние (м или км):',
    )
    return DISTANCE


@except_function
def get_distance(update, _):
    execution = (
        'UPDATE Reports SET distance = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)
    reply_message(update, 'Средний темп:')

    return AVG_PACE


@except_function
def get_avg_pace(update, _):
    execution = (
        'UPDATE Reports SET avg_pace = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)
    reply_message(update, 'Средний пульс:')

    return AVG_HEART_RATE


@except_function
def get_avg_heart_rate(update, context):
    execution = (
        'UPDATE Reports SET avg_heart_rate = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)

    get_name = (
        'SELECT name, last_name FROM Students WHERE chat_id = ?',
        (update.effective_chat.id,),
    )
    name = get_data_db(DATABASE, get_name, method=Cursor.fetchone)
    fullname = f'{name[0]} {name[1]}'

    get_data = (
        '''SELECT report, distance, avg_pace, avg_heart_rate
        FROM Reports WHERE chat_id = ?''',
        (update.effective_chat.id,),
    )
    report_data = get_data_db(DATABASE, get_data, method=Cursor.fetchone)

    message = (
        f'Отчёт после тренировки студента {fullname}\n'
        f'{report_data[0]}\n'
        f'Расстояние: {report_data[1]}\n'
        f'Средний темп: {report_data[2]}\n'
        f'Средний пульс: {report_data[3]}'
    )
    send_message(context, TRAINER_ID, message)
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
def cancel(update, context):
    send_message(context, update.effective_chat.id, 'Диалог завершен')

    return ConversationHandler.END


@except_function
def invalid_report(update, _):
    reply_message(update, 'Отправь фото!')


@except_function
def invalid_input(update, _):
    reply_message(update, 'Некорректные данные.')


report_handler = ConversationHandler(
    entry_points=[CommandHandler(REPORT, send_report)],
    states={
        START: [
            MessageHandler(Filters.regex(r'^[^/].+$'), get_report),
        ],
        DISTANCE: [MessageHandler(Filters.regex(NUMBER_REGEX), get_distance)],
        AVG_PACE: [MessageHandler(Filters.regex(NUMBER_REGEX), get_avg_pace)],
        AVG_HEART_RATE: [
            MessageHandler(Filters.regex(NUMBER_REGEX), get_avg_heart_rate),
            CallbackQueryHandler(get_screenshot, pattern=r'^screen$'),
            CallbackQueryHandler(cancel, pattern=r'^end$'),
        ],
        SCREENSHOT: [
            MessageHandler(Filters.photo, send_screenshot),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_input)],
)
