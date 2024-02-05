from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot.commands.command_list import (
    START_COMMAND,
    STRAVA_LOGIN,
    REGISTRATION_COMMAND,
    FEELING_COMMAND,
    REPORT_COMMAND,
    SEND_WORKOUT_COMMAND,
    DELETE_COMMAND,
)
from bot.config import LOGIN_URL, TRAINER_ID
from bot.utilities import (
    reply_message,
    send_message,
    Database,
    Student,
)


def start(update, _):
    commands = [
        {
            'command': f'/{START_COMMAND}',
            'description': 'информация о командах.',
        },
        {
            'command': f'/{REGISTRATION_COMMAND}',
            'description': 'команда для регистрации, для того, '
            'чтобы отправлять тренеру информацию о тебе',
        },
        {
            'command': f'/{FEELING_COMMAND}',
            'description': 'команда для отправки утреннего '
            'отчёта о своём самочувствие',
        },
        {
            'command': f'/{REPORT_COMMAND}',
            'description': 'команда для отправки отчёта после '
            'тренировки вместе с данными из Strava, можно приложить скриншоты.',
        },
        {
            'command': f'/{SEND_WORKOUT_COMMAND}',
            'description': 'команда, доступная только тренеру, '
            'служит для отправки тренировок спортсменам',
        },
        {
            'command': f'/{STRAVA_LOGIN}',
            'description': 'команда для авторизации через Strava, '
            'чтобы можно было получать данные из приложения',
        },
        {
            'command': f'/{DELETE_COMMAND}',
            'description': 'команда для удаления учётной записи',
        },
    ]

    commands_text = '<b>Список команд:</b>\n\n'
    for cmd in commands:
        commands_text += f'{cmd["command"]} - {cmd["description"]}\n'

    message_text = f'{commands_text}'

    update.message.reply_text(message_text, parse_mode=ParseMode.HTML)


start_handler = CommandHandler(START_COMMAND, start)


def strava_login(update, _):
    chat_id = update.effective_chat.id
    students = Student()
    students.get_all_students()

    if update.effective_chat.id != TRAINER_ID:
        if chat_id not in students:
            reply_message(update, 'Ты не зарегистрирован, пройди регистрацию!')
        else:
            url = LOGIN_URL + f'?chat_id={chat_id}'
            reply_message(
                update,
                'Чтобы авторизоваться через Strava перейди по этой ссылке:  \n'
                f'{url}',
            )
    else:
        reply_message(update, 'Тренеру не нужно авторизовываться')


def start_delete(update, _):
    students = Student()
    students.get_all_students()
    chat_id = update.effective_chat.id

    if update.effective_chat.id != TRAINER_ID:
        if chat_id not in students:
            reply_message(update, 'Ты не зарегистрирован!')
        else:
            buttons = [
                [InlineKeyboardButton('Да', callback_data='delete')],
            ]

            reply_markup = InlineKeyboardMarkup(buttons)

            reply_message(
                update,
                'Ты уверен, что хочешь удалить регистрацию?',
                reply_markup,
            )
    else:
        reply_message(update, 'Ты тренер, тебе нечего удалять)')


def delete(update, context):
    chat_id = update.effective_chat.id
    delete_account = ('DELETE FROM students WHERE chat_id = %s', (chat_id,))
    db = Database()
    db.execute(delete_account)
    send_message(context, chat_id, 'Твои данные удалены')


auth_strava_handler = CommandHandler(STRAVA_LOGIN, strava_login)
delete_handler = CommandHandler(DELETE_COMMAND, start_delete)
delete_callback = CallbackQueryHandler(delete, pattern=r'^delete$')
