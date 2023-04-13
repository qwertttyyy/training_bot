from telegram import Bot
from telegram.ext import Updater

from bot.constants import TOKEN
from conversations.registration import reg_handler
from conversations.feeling import feeling_handler
from conversations.report import report_handler
from conversations.workout import workout_handler


# TODO: Сделать меню из всех команд

def send_reminders(_):
    # c = context
    ...


def start_bot():
    bot = Bot(TOKEN)
    updater = Updater(bot=bot, use_context=True)
    dp = updater.dispatcher
    # job = updater.job_queue
    # job.run_repeating(send_remind, interval=100, first=1)

    dp.add_handler(reg_handler)
    dp.add_handler(feeling_handler)
    dp.add_handler(workout_handler)
    dp.add_handler(report_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    start_bot()
