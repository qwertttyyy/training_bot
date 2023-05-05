from datetime import timedelta, time
from time import sleep

from telegram import Bot
from telegram.ext import Updater

from bot.commands.commands import start_handler
from bot.utilities import get_students_ids, get_data_db
from config import BOT_TOKEN, DATABASE, SPREADSHEET_ID
from bot.conversations.registration import reg_handler
from bot.conversations.feeling import feeling_handler
from bot.conversations.report import report_handler
from bot.conversations.workout import workout_handler
from google_sheets.sheets import GoogleSheet


# TODO: Сделать отдельную команду для отчёта после трени с пaрам расстояние,
#  средний темп, средний пульс из стравы


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


def send_reminders(bot):
    students = get_students_ids(DATABASE)

    for student in students:
        bot.bot.send_message(
            chat_id=student,
            text='Не забудь отправить утренний отчёт, если ещё не отправлял!',
        )


def start_bot():
    bot = Bot(BOT_TOKEN)
    updater = Updater(bot=bot, use_context=True)
    dp = updater.dispatcher
    job = updater.job_queue
    job.run_repeating(
        send_reminders, interval=timedelta(days=1), first=time(9, 0, 0)
    )
    job.run_repeating(
        archive, interval=timedelta(weeks=1), first=time(3, 0, 0)
    )
    dp.add_handler(reg_handler)
    dp.add_handler(feeling_handler)
    dp.add_handler(workout_handler)
    dp.add_handler(report_handler)

    dp.add_handler(start_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    start_bot()
