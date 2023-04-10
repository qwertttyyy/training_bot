import sqlite3
from sqlite3 import Cursor


def db_execute(database, execution):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(*execution)
    conn.commit()
    cursor.close()
    conn.close()


def get_data_db(database, execution, method=None):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(*execution)
    result = cursor.fetchall()

    if method is Cursor.fetchone:
        result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result
