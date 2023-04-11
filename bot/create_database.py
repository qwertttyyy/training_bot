from bot.constants import DATABASE
from utilities import db_execute

CREATE_STUDENTS = '''CREATE TABLE Students (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        last_name TEXT NOT NULL
                        )'''

CREATE_WORKOUTS = '''CREATE TABLE IF NOT EXISTS Workouts (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   chat_id INTEGER NOT NULL
            );'''

CREATE_FEELINGS = ('''CREATE TABLE IF NOT EXISTS Feelings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                feeling INTEGER,
                sleep INTEGER,
                pulse INTEGER
                );''',)

CREATE_REPORTS = ('''CREATE TABLE IF NOT EXISTS Reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL
                    )''')

db_execute(DATABASE, CREATE_FEELINGS)
