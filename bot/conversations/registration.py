from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters, CallbackQueryHandler,
)

from bot.commands.command_list import REGISTRATION
from bot.exceptions import SheetCreateError, ChatDataError
from config import TRAINER_ID, DATABASE, SPREADSHEET_ID
from bot.utilities import (
    db_execute,
    get_students_ids,
    except_function,
    reply_message,
    db_logger, message_logger, send_message, cancel_markup,
)
from google_sheets.sheets import GoogleSheet, sheet_logger

NAME, LAST_NAME = range(2)
KEY = 'name'


@except_function
def start_registration(update, _):
    students_ids = get_students_ids(DATABASE)
    chat_id = update.effective_chat.id

    if chat_id in students_ids:
        reply_message(update, 'Ты уже зарегистрирован!')
        return ConversationHandler.END

    if chat_id != TRAINER_ID:
        reply_message(
            update,
            'Привет! Тебе нужно зарегистрироваться.'
            '\nВведи своё имя: (только имя)',
            cancel_markup
        )

        return NAME

    reply_message(update, 'Ты тренер, тебе не нужно регистрироваться)')

    return ConversationHandler.END


@except_function
def get_name(update, context):
    name = update.message.text
    context.chat_data[KEY] = name

    reply_message(
        update, 'Введи свою фамилию: (только фамилия)', cancel_markup
    )

    return LAST_NAME


@except_function
def get_last_name(update, context):
    chat_id = update.effective_chat.id
    name = context.chat_data.get(KEY)

    if not name:
        message_logger.exception(f'Отсутствует переменная {KEY}')
        raise ChatDataError()

    last_name = update.message.text
    fullname = f'{name} {last_name}'

    try:
        gs = GoogleSheet(SPREADSHEET_ID)
        sheet_id = gs.add_student_sheet(fullname)
        archive_sheet_id = gs.add_sheet(fullname + ' АРХИВ')
    except Exception:
        sheet_logger.exception(
            f'Ошибка добавления листа для {fullname} {chat_id}'
        )
        raise SheetCreateError()

    if context.chat_data.get(KEY):
        del context.chat_data[KEY]

    write_data = (
        '''INSERT INTO Students
         (chat_id, name, last_name, sheet_id, archive_id)
          VALUES (?, ?, ?, ?, ?)''',
        (chat_id, name, last_name, sheet_id, archive_sheet_id)
    )
    db_execute(DATABASE, write_data)

    reply_message(update, 'Ты зарегистрирован.')
    db_logger.info(f'Зарегистрирован пользователь: {fullname} - {chat_id}')

    return ConversationHandler.END


def cancel(update, context):
    send_message(context, update.effective_chat.id, 'Отменено')

    if context.chat_data.get(KEY):
        del context.chat_data[KEY]

    return ConversationHandler.END


@except_function
def invalid_name(update, _):
    reply_message(
        update, 'Имя и фамилия должны состоять из букв! Введи заново.'
    )


reg_handler = ConversationHandler(
    entry_points=[
        CommandHandler(REGISTRATION, start_registration),
    ],
    states={
        NAME: [
            MessageHandler(Filters.regex(r'^[a-zA-Zа-яА-Я]+$'), get_name),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
        LAST_NAME: [
            MessageHandler(Filters.regex(r'^[a-zA-Zа-яА-Я]+$'), get_last_name),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_name)],
)
