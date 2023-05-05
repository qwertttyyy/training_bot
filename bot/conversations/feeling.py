from sqlite3 import Cursor

from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
)
from bot.utilities import (
    db_execute,
    get_data_db,
    get_student_name,
    reply_message,
    except_function,
    send_message,
)
from bot.commands.command_list import FEELING
from config import TRAINER_ID, DATABASE, SPREADSHEET_ID
from bot.utilities import get_students_ids
from google_sheets.sheets import GoogleSheet

FEEl, SLEEP, PULS = range(3)


@except_function
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
        )

        return FEEl
    reply_message(update, 'Ты тренер, тебе не нужно отправлять отчёты)')

    return ConversationHandler.END


@except_function
def get_feeling(update, _):
    execution = (
        'UPDATE Feelings SET feeling = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)
    reply_message(update, 'Сколько ты спал? (ч.)')

    return SLEEP


@except_function
def get_sleep_hours(update, _):
    execution = (
        'UPDATE Feelings SET sleep = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)
    reply_message(update, 'Какой у тебя пульс?')

    return PULS


@except_function
def get_puls(update, context):
    execution = (
        'UPDATE Feelings SET pulse = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)

    get_data = (
        'SELECT feeling, sleep, pulse FROM Feelings WHERE chat_id = ?',
        (update.effective_chat.id,),
    )
    feelings = get_data_db(DATABASE, get_data, method=Cursor.fetchone)

    name = get_student_name(DATABASE, update.effective_chat.id)
    fullname = f'{name[0]} {name[1]}'

    message = (
        f'Утренний отчёт студента {fullname}:\n'
        f'Оценка самочувствия: {feelings[0]}\n'
        f'Количество часов сна: {feelings[1]}\n'
        f'Пульс: {feelings[2]}'
    )
    send_message(context, TRAINER_ID, message)
    reply_message(update, 'Отчёт отправлен тренеру!')
    gs = GoogleSheet(SPREADSHEET_ID)
    gs.send_to_table(feelings, fullname, 'B')

    return ConversationHandler.END


@except_function
def invalid_feeling(update, _):
    reply_message(update, 'Вводи только соответствующие цифры!')


feeling_handler = ConversationHandler(
    entry_points=[CommandHandler(FEELING, send_feeling)],
    states={
        FEEl: [MessageHandler(Filters.regex(r'^([1-9]|10)$'), get_feeling)],
        SLEEP: [
            MessageHandler(
                Filters.regex(r'^\d{1,2}(\.\d{1,2})?$'), get_sleep_hours
            )
        ],
        PULS: [MessageHandler(Filters.regex(r'^\d{2,3}$'), get_puls)],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_feeling)],
)
