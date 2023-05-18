from bot.config import DATABASE
from bot.utilities import db_execute

CREATE_STUDENTS = (
    '''CREATE TABLE IF NOT EXISTS Students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                sheet_id INTEGER,
                archive_id INTEGER,
                is_send_morning INTEGER NOT NULL,
                is_send_evening INTEGER NOT NULL,
                tokens TEXT
                )''',
)

db_execute(DATABASE, CREATE_STUDENTS)
