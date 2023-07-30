from bot.config import DATABASE
from bot.utilities import db_execute

CREATE_STUDENTS = (
    '''CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                sheet_id BIGINT,
                archive_id BIGINT,
                is_send_morning INT NOT NULL,
                is_send_evening INT NOT NULL,
                is_send_strava INT NOT NULL,
                tokens TEXT
                )''',
)

db_execute(DATABASE, CREATE_STUDENTS)
print('База успешно создана')
