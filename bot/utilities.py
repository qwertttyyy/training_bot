import sqlite3
from sqlite3 import Cursor
from typing import Callable

from telegram.ext import ConversationHandler

from bot.exceptions import (
    DatabaseExecutionError,
    SendToGoogleSheetsError,
    SendMessageError,
    ReplyMessageError,
    DatabaseGetDataError,
    SheetCreateError,
)
from config import (
    DB_LOGFILE,
    MESSAGES_LOGFILE,
    UNKNOWN_LOGFILE,
)
from log.logs_config import setup_logger

db_logger = setup_logger('DATABASE_LOGGER', DB_LOGFILE)
message_logger = setup_logger('MESSAGE_LOGGER', MESSAGES_LOGFILE)
unknown_logger = setup_logger('UNKNOWN_LOGGER', UNKNOWN_LOGFILE)

EXCEPTIONS = [
    SendToGoogleSheetsError,
    DatabaseExecutionError,
    DatabaseGetDataError,
    SendMessageError,
    ReplyMessageError,
    SheetCreateError,
]


def db_execute(database: str, execution: tuple):
    try:
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        cursor.execute(*execution)
        conn.commit()
        cursor.close()
        conn.close()
        db_logger.info(f'Запись в бд {execution}')
    except Exception:
        db_logger.exception(f'Ошибка операции с базой {execution}')
        raise DatabaseExecutionError()


def get_data_db(
    database: str, execution: tuple, method: Callable[[Cursor], list] = None
):
    try:
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        cursor.execute(*execution)

        if method is Cursor.fetchone:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
        db_logger.info(f'Получение данных {result} из бд')
        cursor.close()
        conn.close()

        return result
    except Exception:
        db_logger.exception(f'Ошибка получения данных {execution} из базы')
        raise DatabaseGetDataError()


def get_students_ids(database: str):
    execution = ('SELECT chat_id FROM Students',)
    students_ids = tuple(
        student[0]
        for student in get_data_db(database, execution, method=Cursor.fetchall)
    )
    return students_ids


def get_student_name(database: str, chat_id) -> list[str]:
    get_name = (
        'SELECT name, last_name FROM Students WHERE chat_id = ?',
        (chat_id,),
    )
    name = get_data_db(database, get_name, method=Cursor.fetchone)

    return name


def send_message(context, chat_id, message, reply_markup=None):
    try:
        context.bot.send_message(
            chat_id=chat_id, text=message, reply_markup=reply_markup
        )
        message_logger.info(f'Отправка сообщения ')
    except Exception:
        message_logger.exception(
            f'Ошибка отправки сообщения {message} -> {chat_id}'
        )
        raise SendMessageError()


def reply_message(update, message, reply_markup=None):
    try:
        update.message.reply_text(message, reply_markup=reply_markup)
        message_logger.info(f'Ответ сообщением - {message}')
    except Exception:
        message_logger.exception('Ошибка ответа на сообщение.')
        raise ReplyMessageError()


def except_function(func):
    def wrapper(update, context):
        try:
            return func(update, context)
        except Exception as e:
            if e.__class__ not in EXCEPTIONS:
                unknown_logger.exception(f'Ошибка: {e}')
            message = (
                'Что-то пошло не так, отправьте команду '
                'заново или свяжитесь с @disinfect2'
            )
            send_message(context, update.effective_chat.id, message)
            return ConversationHandler.END

    return wrapper
