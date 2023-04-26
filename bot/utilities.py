import sqlite3
from sqlite3 import Cursor
from typing import Callable
from datetime import datetime as dt

from config import DB_LOGFILE, MESSAGES_LOGFILE, SHEETS_LOGFILE
from google_sheets.sheets import GoogleSheet
from log.logs_config import setup_logger

db_logger = setup_logger('DATABASE_LOGGER', DB_LOGFILE)
message_logger = setup_logger('MESSAGE_LOGGER', MESSAGES_LOGFILE)
sheet_logger = setup_logger('SHEET_LOGGER', SHEETS_LOGFILE)


def send_to_table(spreadsheet_id, data: list[int], name, first_column: str):
    try:
        gs = GoogleSheet(spreadsheet_id)
        sheet_range = name + '!A2:A'
        sheet_logger.info()
        dates = gs.get_data(sheet_range)
        today = dt.today().date()

        for column_index in range(1, len(dates) + 1):
            date = dates[column_index - 1]

            if date:
                date = dt.strptime(date[0].split(', ')[1], '%d.%m.%Y').date()
                if date == today:
                    sheet_data = f'{name}!{first_column}{column_index + 1}'
                    gs.add_data(sheet_data, [data])
                    sheet_logger.info(
                        f'Данные успешно добавлены в таблицу {sheet_data}'
                    )
                    break

    except Exception as e:
        sheet_logger.error(f'Ошибка записи в таблицу. {e}')


def db_execute(database: str, execution: tuple):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(*execution)
    conn.commit()
    cursor.close()
    conn.close()


def get_data_db(
        database: str, execution: tuple,
        method: Callable[[Cursor], list] = None
):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(*execution)

    if method is Cursor.fetchone:
        result = cursor.fetchone()
    else:
        result = cursor.fetchall()

    cursor.close()
    conn.close()

    return result


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


def send_message(context, chat_id, message, reply_markup):
    try:
        context.bot.send_message(
            chat_id=chat_id, text=message, reply_markup=reply_markup
        )
    except Exception as e:
        print(f'Ошибка отправки сообщения. {e}')


def reply_message(update, message, reply_markup=None):
    try:
        update.message.reply_text(message, reply_markup)
    except Exception as e:
        print(f'')
