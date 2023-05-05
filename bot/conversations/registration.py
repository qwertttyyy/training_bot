from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
)

from bot.commands.command_list import REGISTRATION
from bot.exceptions import SheetCreateError
from config import TRAINER_ID, DATABASE, SPREADSHEET_ID
from bot.utilities import (
    db_execute,
    get_students_ids,
    get_student_name,
    except_function,
    reply_message,
    db_logger,
)
from google_sheets.sheets import GoogleSheet, sheet_logger

NAME, LAST_NAME = range(2)


@except_function
def start_registration(update, _):
    students_ids = get_students_ids(DATABASE)
    chat_id = update.effective_chat.id

    if chat_id in students_ids:
        reply_message(update, 'Ты уже зарегистрирован!')
        return ConversationHandler.END

    if chat_id != TRAINER_ID:
        reply_message(
            update,
            'Привет! Тебе нужно зарегистрироваться.'
            '\nВведи своё имя: (только имя)',
        )
        registrate = (
            'INSERT INTO Students (chat_id, name, last_name) VALUES (?, ?, ?)',
            (chat_id, 'Name', 'Surname'),
        )
        db_execute(DATABASE, registrate)
        to_feeling = (
            '''INSERT INTO Feelings (chat_id) 
            SELECT ? WHERE NOT EXISTS 
            (SELECT chat_id FROM Feelings WHERE chat_id = ?)''',
            (chat_id, chat_id),
        )
        db_execute(DATABASE, to_feeling)
        to_reports = (
            '''INSERT INTO Reports (chat_id) 
            SELECT ? WHERE NOT EXISTS 
            (SELECT chat_id FROM Reports WHERE chat_id = ?)''',
            (chat_id, chat_id),
        )

        db_execute(DATABASE, to_reports)

        return NAME

    reply_message(update, 'Ты тренер, тебе не нужно регистрироваться)')

    return ConversationHandler.END


@except_function
def get_name(update, _):
    execution = (
        'UPDATE Students SET name = ? WHERE chat_id = ?',
        (update.message.text, update.effective_chat.id),
    )
    db_execute(DATABASE, execution)
    reply_message(update, 'Введи свою фамилию: (только фамилия)')

    return LAST_NAME


@except_function
def get_last_name(update, _):
    chat_id = update.effective_chat.id
    execution = (
        'UPDATE Students SET last_name = ? WHERE chat_id = ?',
        (update.message.text, chat_id),
    )
    db_execute(DATABASE, execution)

    name = get_student_name(DATABASE, chat_id)
    fullname = f'{name[0]} {name[1]}'
    try:
        gs = GoogleSheet(SPREADSHEET_ID)
        sheet_id = gs.add_student_sheet(fullname)
        archive_sheet_id = gs.add_sheet(fullname + ' АРХИВ')
    except Exception:
        sheet_logger.exception(
            f'Ошибка добавления листа для {fullname} {chat_id}'
        )
        delete_student = ('DELETE FROM Students WHERE chat_id = ?', chat_id)
        db_execute(DATABASE, delete_student)
        raise SheetCreateError()

    execution = (
        'UPDATE Students SET sheet_id = ?, archive_id = ? WHERE chat_id = ?',
        (sheet_id, archive_sheet_id, chat_id),
    )
    db_execute(DATABASE, execution)

    reply_message(update, 'Ты зарегистрирован.')
    db_logger.info(f'Зарегистрирован пользователь: {fullname} - {chat_id}')
    return ConversationHandler.END


@except_function
def invalid_name(update, _):
    reply_message(
        update, 'Имя и фамилия должны состоять из букв! Введи заново.'
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
