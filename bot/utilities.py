import sqlite3
from sqlite3 import Cursor
from typing import Callable


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
            method=Cursor.fetchall)
        )

    return students_ids
