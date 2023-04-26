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
from bot.constants import DATABASE, TRAINER_ID, SPREADSHEET_ID
from bot.utilities import (
    get_students_ids,
    get_data_db,
    db_execute,
    send_to_table,
)

START, DISTANCE, AVG_PACE, AVG_HEART_RATE, SCREENSHOT = range(5)
NUMBER_REGEX = r'^[0-9]+[.]?([0-9]+)?$'


def send_report(update, _):
    students_ids = get_students_ids(DATABASE)
    chat_id = update.effective_chat.id

    if update.effective_chat.id != TRAINER_ID:
        if chat_id not in students_ids:
            update.message.reply_text(
                'Ты не зарегистрирован, пройди регистрацию!'
            )

            return ConversationHandler.END

        update.message.reply_text(
            'Отправь отчёт после тренировки.\nВведи отчёт:',
        )

        return START
    update.message.reply_text('Ты тренер, тебе не нужно отправлять отчёты)')
    return ConversationHandler.END


def get_report(update, _):
    execution = (
        'UPDATE Reports SET report = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)
    update.message.reply_text(
        'Теперь вводи данные из Strava.\n' 'Расстояние (км):'
    )
    return DISTANCE


def get_distance(update, _):
    execution = (
        'UPDATE Reports SET distance = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)
    update.message.reply_text('Средний темп:')

    return AVG_PACE


def get_avg_pace(update, _):
    execution = (
        'UPDATE Reports SET avg_pace = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)
    update.message.reply_text('Средний пульс:')

    return AVG_HEART_RATE


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
    context.bot.send_message(chat_id=TRAINER_ID, text=message)
    send_to_table(SPREADSHEET_ID, report_data[1:], fullname, 'F')

    buttons = [
        [InlineKeyboardButton('Отправить скриншот', callback_data='screen')],
        [InlineKeyboardButton('Завершить', callback_data='end')],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    update.message.reply_text(
        'Отчёт отправлен тренеру.\n'
        'Теперь можешь отправить скриншот, либо заверши диалог',
        reply_markup=reply_markup,
    )


def get_screenshot(update, context):
    context.bot.send_message(
        text='Отправь скриншот', chat_id=update.effective_chat.id
    )
    return SCREENSHOT


def send_screenshot(update, context):
    screenshot = update.message.photo[-1]
    context.bot.send_photo(chat_id=TRAINER_ID, photo=screenshot)
    update.message.reply_text('Скриншот отправлен тренеру. Диалог завершен.')

    return ConversationHandler.END


def cancel(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='Диалог завершен'
    )

    return ConversationHandler.END


def invalid_report(bot, _):
    bot.message.reply_text('Отправь фото!')


def invalid_input(bot, _):
    bot.message.reply_text('Некорректные данные.')


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
