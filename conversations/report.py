from sqlite3 import Cursor

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    CallbackQueryHandler,
)

from bot.commands import REPORT
from bot.constants import DATABASE, TRAINER_ID
from bot.utilities import get_students_ids, get_data_db

START, SCREENSHOT = range(2)


def send_report(update, _):
    students_ids = get_students_ids(DATABASE)
    chat_id = update.effective_chat.id
    if chat_id not in students_ids:
        update.message.reply_text('Ты не зарегистрирован, пройди регистрацию!')
        return ConversationHandler.END

    if update.effective_chat.id != TRAINER_ID:
        buttons = [
            [
                InlineKeyboardButton(
                    'Отправить скриншот', callback_data='screen'
                )
            ],
            [InlineKeyboardButton('Завершить', callback_data='end')],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        update.message.reply_text(
            'Отправь отчёт после тренировки.\n', reply_markup=reply_markup
        )
        update.message.reply_text('Введи отчёт:')

        return START
    update.message.reply_text('Ты тренер, тебе не нужно отправлять отчёты)')
    return ConversationHandler.END


def get_report(update, context):
    get_name = (
        'SELECT name, last_name FROM Students WHERE chat_id = ?',
        (update.effective_chat.id,),
    )
    name = get_data_db(DATABASE, get_name, method=Cursor.fetchone)
    message = (
        f'Отчёт после тренировки студента {name[0]} {name[1]}\n'
        f'{update.message.text}'
    )
    context.bot.send_message(chat_id=TRAINER_ID, text=message)

    update.message.reply_text(
        'Отчёт отправлен\n'
        'Теперь можешь отправить скриншот, '
        'либо заверши диалог'
    )
    return START


def get_screenshot(update, context):
    context.bot.send_message(
        text='Отправь скриншот', chat_id=update.effective_chat.id
    )
    return SCREENSHOT


def send_screenshot(update, context):
    screenshot = update.message.photo[-1]
    context.bot.send_photo(chat_id=TRAINER_ID, photo=screenshot)
    update.message.reply_text('Скриншот отправлен тренеру. Диалог завершен.')
    return ConversationHandler.END


def cancel(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='Диалог завершен'
    )
    return ConversationHandler.END


def invalid_report(bot, _):
    bot.message.reply_text('Отправь фото!')


report_handler = ConversationHandler(
    entry_points=[CommandHandler(REPORT, send_report)],
    states={
        START: [
            CallbackQueryHandler(get_screenshot, pattern=r'^screen$'),
            CallbackQueryHandler(cancel, pattern=r'^end$'),
            MessageHandler(Filters.text, get_report),
        ],
        SCREENSHOT: [MessageHandler(Filters.photo, send_screenshot)],
    },
    fallbacks=[MessageHandler(Filters.photo, invalid_report)],
)
