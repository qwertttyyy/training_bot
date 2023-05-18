from sqlite3 import Cursor
from time import sleep

from telegram import ParseMode
from telegram.ext import CommandHandler

from bot.commands.command_list import START_COMMAND, STRAVA_LOGIN
from bot.utilities import reply_message, db_execute, get_data_db
from config import LOGIN_URL, DATABASE


def start(update, _):
    commands = [
        {'command': '/start', 'description': 'информация о командах.'},
        {
            'command': '/registration',
            'description': 'команда для регистрации, для того, чтобы отправлять тренеру информацию о тебе',
        },
        {
            'command': '/feeling',
            'description': 'команда для отправки утреннего отчёта о своём самочувствие',
        },
        {
            'command': '/report',
            'description': 'команда для отправки отчёта после тренировки, можно приложить скриншот',
        },
        {
            'command': '/sendworkout',
            'description': 'команда, доступная только тренеру, служит для отправки тренировок спортсменам.',
        },
    ]

    commands_text = '<b>Список команд:</b>\n\n'
    for cmd in commands:
        commands_text += (
            f'<code>{cmd["command"]}</code> - {cmd["description"]}\n'
        )

    message_text = f'<pre>{commands_text}</pre>'

    update.message.reply_text(message_text, parse_mode=ParseMode.HTML)


start_handler = CommandHandler(START_COMMAND, start)


def strava_login(update, _):
    chat_id = update.effective_chat.id
    url = LOGIN_URL + f'?chat_id={chat_id}'
    reply_message(
        update,
        'Чтобы авторизоваться через Strava перейди по этой ссылке:  \n'
        f'{url}',
    )
    while True:
        tokens = get_data_db(
            DATABASE,
            ('SELECT tokens FROM Students WHERE chat_id = ?', (chat_id,)),
            Cursor.fetchone,
        )[0]
        if tokens:
            reply_message(
                update,
                'Авторизация прошла успешно. Теперь ты можешь '
                'отправлять данные автоматически из приложения Strava',
            )
            break
        sleep(1)


strava_handler = CommandHandler(STRAVA_LOGIN, strava_login)
