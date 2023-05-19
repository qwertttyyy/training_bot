from datetime import datetime as dt

from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)

from bot.exceptions import ChatDataError
from bot.utilities import (
    get_student_name,
    reply_message,
    catch_exception,
    send_message,
    message_logger,
    clean_chat_data,
    cancel_markup,
    db_execute,
)
from bot.commands.command_list import FEELING_COMMAND
from bot.config import TRAINER_ID, DATABASE, SPREADSHEET_ID
from bot.utilities import get_students_ids
from bot.google_sheets.sheets import GoogleSheet

FEEl, SLEEP, PULSE = range(3)
DATA_KEYS = ['feel', 'sleep', 'pulse']


@catch_exception
def send_feeling(update, _):
    students_ids = get_students_ids(DATABASE)
    chat_id = update.effective_chat.id

    if update.effective_chat.id != TRAINER_ID:
        if chat_id not in students_ids:
            reply_message(update, 'Ты не зарегистрирован, пройди регистрацию!')

            return ConversationHandler.END

        reply_message(
            update,
            'Отправь отчёт о своём состоянии.\n'
            'Как ты себя сейчас чувствуешь (от 1 до 10) ?',
            cancel_markup,
        )

        return FEEl
    reply_message(update, 'Ты тренер, тебе не нужно отправлять отчёты)')

    return ConversationHandler.END


@catch_exception
def get_feeling(update, context):
    context.chat_data[DATA_KEYS[0]] = update.message.text
    reply_message(update, 'Сколько ты спал? (ч.)', cancel_markup)

    return SLEEP


@catch_exception
def get_sleep_hours(update, context):
    context.chat_data[DATA_KEYS[1]] = update.message.text
    reply_message(update, 'Какой у тебя пульс?', cancel_markup)

    return PULSE


@catch_exception
def get_puls(update, context):
    chat_id = update.effective_chat.id

    context.chat_data[DATA_KEYS[2]] = update.message.text

    feelings = []

    for name in DATA_KEYS:
        data = context.chat_data.get(name)
        if not data:
            message_logger.exception(f'Отсутствует переменная {name}')
            raise ChatDataError()
        feelings.append(data)

    name = get_student_name(DATABASE, update.effective_chat.id)
    fullname = f'{name[0]} {name[1]}'

    message = (
        f'Утренний отчёт студента {fullname}:\n'
        f'Дата: {dt.now().strftime("%d.%m.%Y")}\n'
        f'Оценка самочувствия: {feelings[0]}\n'
        f'Количество часов сна: {feelings[1]}\n'
        f'Пульс: {feelings[2]}'
    )

    clean_chat_data(context, DATA_KEYS)

    send_message(context, TRAINER_ID, message)
    reply_message(update, 'Отчёт отправлен тренеру!')
    send_message(context, chat_id, message)

    gs = GoogleSheet(SPREADSHEET_ID)
    gs.send_to_table(feelings, fullname, 'B')

    db_execute(
        DATABASE,
        (
            'UPDATE students SET is_send_morning = 1 WHERE chat_id = %s',
            (chat_id,),
        ),
    )

    return ConversationHandler.END


@catch_exception
def cancel(update, context):
    send_message(context, update.effective_chat.id, 'Отменено')
    clean_chat_data(context, DATA_KEYS)

    return ConversationHandler.END


@catch_exception
def invalid_feeling(update, _):
    reply_message(update, 'Вводи только соответствующие цифры!')


feeling_handler = ConversationHandler(
    entry_points=[CommandHandler(FEELING_COMMAND, send_feeling)],
    states={
        FEEl: [
            MessageHandler(Filters.regex(r'^([1-9]|10)$'), get_feeling),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
        SLEEP: [
            MessageHandler(
                Filters.regex(r'^\d{1,2}([.,]\d{1,2})?$'), get_sleep_hours
            ),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
        PULSE: [
            MessageHandler(Filters.regex(r'^\d{2,3}$'), get_puls),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_feeling)],
)
