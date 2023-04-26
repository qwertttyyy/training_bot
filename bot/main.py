from telegram import Bot
from telegram.ext import Updater

from bot.commands.commands import start_handler
from config import BOT_TOKEN
from bot.conversations.registration import reg_handler
from bot.conversations.feeling import feeling_handler
from bot.conversations.report import report_handler
from bot.conversations.workout import workout_handler


# TODO: Сделать отдельную команду для отчёта после трени с пaрам расстояние,
#  средний темп, средний пульс из стравы


def send_reminders(_):
    # TODO: Рассылка напоминаний об утреннем отчёте
    ...


def start_bot():
    bot = Bot(BOT_TOKEN)
    updater = Updater(bot=bot, use_context=True)
    dp = updater.dispatcher
    # job = updater.job_queue
    # job.run_repeating(send_remind, interval=100, first=1)

    dp.add_handler(reg_handler)
    dp.add_handler(feeling_handler)
    dp.add_handler(workout_handler)
    dp.add_handler(report_handler)

    dp.add_handler(start_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    start_bot()
