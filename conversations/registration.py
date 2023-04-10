from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
)

from constants import TRAINER_ID, DATABASE
from utilities import get_data_db, db_execute

NAME, LAST_NAME = range(2)


def start_registration(update, _):
    # TODO: добавить проверку, что пользователь уже зареган
    execution = ('SELECT chat_id FROM Students',)
    students_ids = (student[0] for student in get_data_db(DATABASE, execution))
    chat_id = update.effective_chat.id

    if chat_id in students_ids:
        update.message.reply_text('Ты уже зарегистрирован!')
        return ConversationHandler.END

    if chat_id != TRAINER_ID:
        update.message.reply_text(
            'Привет! Тебе нужно зарегистрироваться.\n Введи своё имя:'
        )
        execution = (
            'INSERT INTO Students (chat_id, name, last_name) VALUES (?, ?, ?)',
            (chat_id, 'Name', 'Surname'),
        )
        db_execute(DATABASE, execution)
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
    update.message.reply_text('Ты зарегистрирован.')
    return ConversationHandler.END


def invalid_name(bot, _):
    bot.message.reply_text(
        'Имя и фамилия должны состоять из букв! Введи заново.'
    )


reg_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start_registration)],
    states={
        NAME: [MessageHandler(Filters.regex(r'^[a-zA-Zа-яА-Я]+$'), get_name)],
        LAST_NAME: [
            MessageHandler(Filters.regex(r'^[a-zA-Zа-яА-Я]+$'), get_last_name)
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_name)],
)
