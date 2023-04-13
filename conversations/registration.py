from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
)

from bot.commands import REGISTRATION
from bot.constants import TRAINER_ID, DATABASE, SPREADSHEET_ID
from bot.utilities import db_execute, get_students_ids, get_student_name
from google_sheets.sheets import GoogleSheet

NAME, LAST_NAME = range(2)


def start_registration(update, _):
    students_ids = get_students_ids(DATABASE)
    chat_id = update.effective_chat.id

    if chat_id in students_ids:
        update.message.reply_text('Ты уже зарегистрирован!')
        return ConversationHandler.END

    if chat_id != TRAINER_ID:
        update.message.reply_text(
            'Привет! Тебе нужно зарегистрироваться.\nВведи своё имя:'
        )
        registrate = (
            'INSERT INTO Students (chat_id, name, last_name) VALUES (?, ?, ?)',
            (chat_id, 'Name', 'Surname'),
        )
        db_execute(DATABASE, registrate)
        to_feeling = ('INSERT INTO Feelings (chat_id) VALUES (?)', (chat_id,))
        db_execute(DATABASE, to_feeling)
        return NAME

    update.message.reply_text('Ты тренер, тебе не нужно регистрироваться)')
    return ConversationHandler.END


def get_name(update, _):
    print(update.message.text)
    execution = (
        'UPDATE Students SET name = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)
    update.message.reply_text('Введи свою фамилию:')
    return LAST_NAME


def get_last_name(update, _):
    print(update.message.text)
    execution = (
        'UPDATE Students SET last_name = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)

    name = get_student_name(DATABASE, update.effective_chat.id)
    fullname = f'{name[0]} {name[1]}'
    gs = GoogleSheet(SPREADSHEET_ID)
    gs.add_sheet(fullname)

    update.message.reply_text('Ты зарегистрирован.')

    return ConversationHandler.END


def invalid_name(bot, _):
    bot.message.reply_text(
        'Имя и фамилия должны состоять из букв! Введи заново.'
    )


reg_handler = ConversationHandler(
    entry_points=[CommandHandler(REGISTRATION, start_registration)],
    states={
        NAME: [MessageHandler(Filters.regex(r'^[a-zA-Zа-яА-Я]+$'), get_name)],
        LAST_NAME: [
            MessageHandler(Filters.regex(r'^[a-zA-Zа-яА-Я]+$'), get_last_name)
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_name)],
)
