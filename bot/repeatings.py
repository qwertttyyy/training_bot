from datetime import datetime as dt
from time import sleep

from bot.config import (
    DATABASE,
    SPREADSHEET_ID,
    STRAVA_ACTIVITIES,
    TRAINER_ID,
)
from bot.google_sheets.sheets import GoogleSheet
from bot.utilities import (
    db_execute,
    get_data_db,
    get_access_data,
    send_message,
    get_training_data,
    get_student_name,
    get_run_activity,
    get_strava_params,
    set_is_send,
    strava_logger,
)


def auto_send_training(context):
    get_students = ('SELECT chat_id, is_send_strava FROM students',)
    students_ids = get_data_db(DATABASE, get_students)

    for student in students_ids:
        chat_id = student[0]
        is_send_strava = student[1]

        if not is_send_strava:
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

                if strava_data:
                    strava_logger.info(
                        f'Автополучение данных тренировки пользователя {chat_id}, '
                        f'target_time: {target_time}'
                    )
                    last_run = get_run_activity(strava_data)
                    training_data = get_strava_params(last_run)

                    if training_data:
                        name = get_student_name(DATABASE, chat_id)
                        fullname = f'{name[0]} {name[1]}'

                        distance, avg_heart_rate, avg_pace, date = (
                            training_data['distance'],
                            training_data['avg_heart_rate'],
                            training_data["avg_pace"],
                            training_data["date"],
                        )

                        message = (
                            f'Данные последней тренировки студента {fullname}\n'
                            f'Дата: {date}\n'
                            f'Расстояние: {distance}\n'
                            f'Средний темп: {avg_pace}\n'
                            f'Средний пульс: {avg_heart_rate}'
                        )

                        send_message(context, TRAINER_ID, message)

                        data_to_table = [
                            distance,
                            avg_pace,
                            avg_heart_rate,
                        ]
                        gs = GoogleSheet(SPREADSHEET_ID)
                        gs.send_to_table(data_to_table, fullname, 'F', date)

                        set_is_send(DATABASE, 'is_send_strava', 1, chat_id)

                        send_message(context, chat_id, message)
                        send_message(
                            context,
                            chat_id,
                            'Данные последней тренировки отправлены тренеру! '
                            'Не забудь отправить отчёт /report',
                        )
                    else:
                        send_message(
                            context,
                            chat_id,
                            'Ошибка получения одного из параметров последней '
                            'тренировки. Попробуй ввести данные вручную',
                        )
                        set_is_send(DATABASE, 'is_send_strava', 1, chat_id)


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
        ('UPDATE Students SET is_send_morning = 0 WHERE is_send_morning = 1',),
    )
    db_execute(
        DATABASE,
        ('UPDATE Students SET is_send_evening = 0 WHERE is_send_evening = 1',),
    )
    db_execute(
        DATABASE,
        ('UPDATE Students SET is_send_strava = 0 WHERE is_send_strava = 1',),
    )
