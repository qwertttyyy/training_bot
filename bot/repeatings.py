from time import sleep

from bot.utilities import get_data_db, db_execute
from config import DATABASE, SPREADSHEET_ID
from google_sheets.sheets import GoogleSheet


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
