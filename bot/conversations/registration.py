from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from bot.commands.command_list import REGISTRATION_COMMAND
from bot.config import DATABASE, SPREADSHEET_ID, TRAINER_ID
from bot.exceptions import ChatDataError, SheetCreateError
from bot.google_sheets.sheets import GoogleSheet, sheet_logger
from bot.utilities import (
    cancel_markup,
    catch_exception,
    db_execute,
    db_logger,
    message_logger,
    reply_message,
    send_message,
    Student,
)

NAME, LAST_NAME = range(2)


@catch_exception
def start_registration(update, _):
    students = Student()
    students.get_all_students()
    chat_id = update.effective_chat.id

    if chat_id in students:
        reply_message(update, "Ты уже зарегистрирован!")
        return ConversationHandler.END

    if chat_id != TRAINER_ID:
        reply_message(
            update,
            "Привет! Тебе нужно зарегистрироваться." "\nВведи своё имя: (только имя)",
            cancel_markup,
        )

        return NAME

    reply_message(update, "Ты тренер, тебе не нужно регистрироваться)")

    return ConversationHandler.END


@catch_exception
def get_name(update, context):
    name = update.message.text
    context.chat_data["name"] = name

    reply_message(update, "Введи свою фамилию: (только фамилия)", cancel_markup)

    return LAST_NAME


@catch_exception
def get_last_name(update, context):
    chat_id = update.effective_chat.id
    name = context.chat_data.get("name")

    if not name:
        message_logger.exception(f"Отсутствует переменная {name}")
        raise ChatDataError()

    last_name = update.message.text
    fullname = f"{name} {last_name}"

    send_message(context, chat_id, "Пара секунд...")

    try:
        gs = GoogleSheet(SPREADSHEET_ID)
        sheet_id = gs.new_student_sheet(fullname)
        archive_sheet_id = gs.archive_sheet(fullname + " АРХИВ")
    except Exception:
        sheet_logger.exception(f"Ошибка создания листа для {fullname} {chat_id}")
        raise SheetCreateError()

    if context.chat_data.get("name"):
        context.chat_data.clear()

        write_data = (
            """INSERT INTO students
             (chat_id, name, last_name, sheet_id, archive_id, is_send_morning, is_send_evening, is_send_strava)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (chat_id, name, last_name, sheet_id, archive_sheet_id, 0, 0, ""),
        )
        db_execute(DATABASE, write_data)

    reply_message(update, "Ты зарегистрирован.")
    db_logger.info(f"Зарегистрирован пользователь: {fullname} - {chat_id}")

    return ConversationHandler.END


def cancel(update, context):
    send_message(context, update.effective_chat.id, "Отменено")
    context.chat_data.clear()
    return ConversationHandler.END


@catch_exception
def invalid_name(update, _):
    reply_message(update, "Имя и фамилия должны состоять из букв! Введи заново.")


reg_handler = ConversationHandler(
    entry_points=[
        CommandHandler(REGISTRATION_COMMAND, start_registration),
    ],
    states={
        NAME: [
            MessageHandler(Filters.regex(r"^[a-zA-Zа-яА-Я]+$"), get_name),
            CallbackQueryHandler(cancel, pattern=r"^cancel$"),
        ],
        LAST_NAME: [
            MessageHandler(Filters.regex(r"^[a-zA-Zа-яА-Я]+$"), get_last_name),
            CallbackQueryHandler(cancel, pattern=r"^cancel$"),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_name)],
)
