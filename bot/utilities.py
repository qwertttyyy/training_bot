import sqlite3
from sqlite3 import Cursor
from typing import Callable

from google_sheets.sheets import GoogleSheet


def db_execute(database: str, execution: tuple):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(*execution)
    conn.commit()
    cursor.close()
    conn.close()


def get_data_db(
        database: str,
        execution: tuple,
        method: Callable[[Cursor], list] = None):
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
    students_ids = (
        student[0] for student in get_data_db(
                                database,
                                execution,
                                method=Cursor.fetchall))

    return students_ids


def get_student_name(database: str, chat_id) -> list[str]:
    get_name = (
        'SELECT name, last_name FROM Students WHERE chat_id = ?',
        (chat_id,)
    )
    name = get_data_db(database, get_name, method=Cursor.fetchone)
    return name
