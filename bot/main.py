from datetime import time, timedelta

from telegram import Bot
from telegram.ext import Updater

from bot.commands.commands import (
    start_handler,
    auth_strava_handler,
    delete_callback,
    delete_handler,
)
from bot.config import BOT_TOKEN, MOSCOW_TZ
from bot.conversations.feeling import feeling_handler
from bot.conversations.registration import reg_handler
from bot.conversations.report import report_handler
from bot.conversations.workout import workout_handler
from bot.repeatings import (
    archive,
    clear_is_send,
    send_evening_reminders,
    send_morning_reminders,
    auto_send_training,
)


def start_bot():
    bot = Bot(BOT_TOKEN)
    updater = Updater(bot=bot, use_context=True)
    dp = updater.dispatcher

    job = updater.job_queue
    job.run_repeating(
        send_morning_reminders,
        interval=timedelta(days=1),
        first=time(9, 0, 0, tzinfo=MOSCOW_TZ),
    )
    job.run_repeating(
        send_evening_reminders,
        interval=timedelta(days=1),
        first=time(22, 0, 0, tzinfo=MOSCOW_TZ),
    )
    job.run_repeating(
        clear_is_send,
        interval=timedelta(days=1),
        first=time(0, 30, 0, tzinfo=MOSCOW_TZ),
    )
    job.run_repeating(
        archive,
        interval=timedelta(weeks=1),
        first=time(3, 0, 0, tzinfo=MOSCOW_TZ),
    )
    job.run_repeating(
        auto_send_training,
        interval=timedelta(minutes=30),
        first=600,
    )

    dp.add_handler(reg_handler)
    dp.add_handler(feeling_handler)
    dp.add_handler(workout_handler)
    dp.add_handler(report_handler)
    dp.add_handler(delete_handler)
    dp.add_handler(delete_callback)

    dp.add_handler(start_handler)
    dp.add_handler(auth_strava_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    start_bot()
