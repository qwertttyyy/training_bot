from datetime import datetime as dt
from http import HTTPStatus
from time import sleep

from bot.config import (
    DATABASE,
    SPREADSHEET_ID,
    STRAVA_ACTIVITIES,
)
from bot.google_sheets.sheets import GoogleSheet
from bot.utilities import (
    db_execute,
    get_data_db,
    get_access_data,
    get_training_data,
    send_trainings_to_trainer,
    send_avg_params_to_table,
    send_message,
)


def auto_send_training(context):
    get_students = ('SELECT chat_id, is_send_strava FROM students',)
    students_ids = get_data_db(DATABASE, get_students)

    for student in students_ids:
        chat_id = student[0]
        access_data = get_access_data(DATABASE, chat_id)

        if access_data:
            access_token = access_data['access_token']

            now = dt.now()
            target_time = now.replace(hour=0, minute=30, second=0)

            target_timestamp = target_time.timestamp()
            params = {'after': int(target_timestamp)}
            strava_data = get_training_data(
                STRAVA_ACTIVITIES, access_token, params
            )

            check_new = False

            if strava_data and strava_data != HTTPStatus.BAD_REQUEST:
                check_new = send_trainings_to_trainer(
                    context, strava_data, chat_id
                )

            if check_new:
                send_avg_params_to_table(strava_data, chat_id)
                send_message(
                    context,
                    chat_id,
                    'Данные последней тренировки отправлены тренеру! '
                    'Не забудь отправить отчёт /report',
                )


def archive(_):
    get_students = (
        'SELECT name, last_name, sheet_id, archive_id FROM Students',
    )
    students = get_data_db(DATABASE, get_students)

    gs = GoogleSheet(SPREADSHEET_ID)

    for student in students:
        fullname = f'{student[0]} {student[1]}'
        values = gs.get_data(f'{fullname}!A1:A')
        if len(values) > 32:
            gs.move_rows_to_another_sheet(
                student[2], student[3], f'{fullname} АРХИВ'
            )
        sleep(3)


def send_morning_reminders(bot):
    students = get_data_db(
        DATABASE, ('SELECT chat_id FROM Students WHERE is_send_morning = 0',)
    )

    for student in students:
        bot.bot.send_message(
            chat_id=student[0],
            text='Не забудь отправить утренний отчёт!',
        )


def send_evening_reminders(bot):
    students = get_data_db(
        DATABASE, ('SELECT chat_id FROM Students WHERE is_send_evening = 0',)
    )

    for student in students:
        bot.bot.send_message(
            chat_id=student[0],
            text='Не забудь отправить отчёт после тренировки!',
        )


def clear_is_send(_):
    db_execute(
        DATABASE,
        ('UPDATE students SET is_send_morning = 0 WHERE is_send_morning = 1',),
    )
    db_execute(
        DATABASE,
        ('UPDATE students SET is_send_evening = 0 WHERE is_send_evening = 1',),
    )
    db_execute(
        DATABASE,
        ("UPDATE students SET is_send_strava = ''",),
    )
