from bot.utilities import Database

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
                is_send_strava TEXT NOT NULL,
                tokens TEXT
                )''',
)
db = Database()
db.execute(CREATE_STUDENTS)
print('База успешно создана')
