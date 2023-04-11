from sqlite3 import Cursor

from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
)
from bot.utilities import db_execute, get_data_db
from bot.commands import FEELING
from bot.constants import TRAINER_ID, DATABASE
from bot.utilities import get_students_ids

FEEl, SLEEP, PULS = range(3)


def send_feeling(update, _):

    students_ids = get_students_ids(DATABASE)
    chat_id = update.effective_chat.id
    if chat_id not in students_ids:
        update.message.reply_text('Ты не зарегистрирован, пройди регистрацию!')
        return ConversationHandler.END

    if update.effective_chat.id != TRAINER_ID:
        update.message.reply_text(
            'Отправь отчёт о своём состоянии.\n'
            'Как ты себя сейчас чувствуешь (от 1 до 10) ?'
        )
        execution = ('INSERT INTO Feelings (chat_id) VALUES (?)', (chat_id,))
        db_execute(DATABASE, execution)
        return FEEl
    update.message.reply_text('Ты тренер, тебе не нужно отправлять отчёты)')
    return ConversationHandler.END


def get_feeling(update, _):
    print(update.message.text)
    execution = (
        'UPDATE Feelings SET feeling = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id)
    )
    db_execute(DATABASE, execution)
    update.message.reply_text('Сколько ты спал?')
    return SLEEP


def get_sleep_hours(update, _):
    print(update.message.text)
    execution = (
        'UPDATE Feelings SET sleep = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id)
    )
    db_execute(DATABASE, execution)
    update.message.reply_text('Какой у тебя пульс?')
    return PULS


def get_puls(update, context):
    print(update.message.text)
    execution = (
        'UPDATE Feelings SET pulse = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id)
    )
    db_execute(DATABASE, execution)
    get_data = (
        'SELECT feeling, sleep, pulse FROM Feelings WHERE chat_id = ?',
        (update.effective_chat.id,)
    )
    feelings = get_data_db(DATABASE, get_data, method=Cursor.fetchone)
    get_name = (
        'SELECT name, last_name FROM Students WHERE chat_id = ?',
        (update.effective_chat.id,)
    )
    name = get_data_db(DATABASE, get_name, method=Cursor.fetchone)
    message = (
        f'Утренний отчёт студента {name[0]} {name[1]}:\n'
        f'Оценка самочувствия: {feelings[0]}\n'
        f'Количество часов сна: {feelings[1]}\n'
        f'Пульс: {feelings[2]}'
    )
    context.bot.send_message(chat_id=TRAINER_ID, text=message)
    update.message.reply_text('Отчёт отправлен тренеру!')
    return ConversationHandler.END


def invalid_feeling(bot, _):
    bot.message.reply_text('Вводи только соответствующие цифры!')


feeling_handler = ConversationHandler(
    entry_points=[CommandHandler(FEELING, send_feeling)],
    states={
        FEEl: [MessageHandler(Filters.regex(r'^([1-9]|10)$'), get_feeling)],
        SLEEP: [
            MessageHandler(Filters.regex(r'^[0-9]{1,2}$'), get_sleep_hours)
        ],
        PULS: [MessageHandler(Filters.regex(r'^\d{2,3}$'), get_puls)],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_feeling)],
)
