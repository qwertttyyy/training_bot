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
    get_training_data,
    send_trainings_to_trainer,
    send_avg_params_to_table,
    send_message,
    Student,
)


def auto_send_training(context):
    students = Student()
    students.get_all_students()
    for student in students:
        chat_id = student.chat_id
        access_data = student.get_access_data()
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
                    context, strava_data, student
                )

            if check_new:
                send_avg_params_to_table(strava_data, student)
                send_message(
                    context,
                    chat_id,
                    'Данные последней тренировки отправлены тренеру! '
                    'Не забудь отправить отчёт /report',
                )


def archive(_):
    gs = GoogleSheet(SPREADSHEET_ID)
    students = Student()
    students.get_all_students()
    for student in students:
        values = gs.get_data(f'{student.full_name}!A1:A')
        if len(values) > 32:
            gs.move_rows_to_another_sheet(
                student.sheet_id,
                student.archive_id,
                f'{student.full_name} АРХИВ',
            )
        sleep(3)


def send_morning_reminders(bot):
    students = Student()
    students.get_all_students()
    for student in students:
        if student.is_send_morning == 0:
            bot.bot.send_message(
                chat_id=student.chat_id,
                text='Не забудь отправить утренний отчёт!',
            )


def send_evening_reminders(bot):
    students = Student()
    students.get_all_students()
    for student in students:
        if student.is_send_evening == 0:
            bot.bot.send_message(
                chat_id=student.chat_id,
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
