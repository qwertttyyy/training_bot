from config import DATABASE
from bot.utilities import db_execute

CREATE_STUDENTS = (
    '''CREATE TABLE IF NOT EXISTS Students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                sheet_id INTEGER,
                archive_id INTEGER,
                tokens TEXT
                )''',
)

CREATE_FEELINGS = (
    '''CREATE TABLE IF NOT EXISTS Feelings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                feeling INTEGER,
                sleep REAL,
                pulse INTEGER
                );''',
)

CREATE_REPORTS = (
    '''CREATE TABLE IF NOT EXISTS Reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                report TEXT,
                distance REAL,
                avg_pace REAL,
                avg_heart_rate REAL
                );''',
)

db_execute(DATABASE, CREATE_STUDENTS)
db_execute(DATABASE, CREATE_FEELINGS)
db_execute(DATABASE, CREATE_REPORTS)
