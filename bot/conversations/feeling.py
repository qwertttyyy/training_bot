from datetime import datetime as dt

from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from bot.commands.command_list import FEELING_COMMAND
from bot.config import DATABASE, SPREADSHEET_ID, TRAINER_ID, DATE_FORMAT
from bot.exceptions import ChatDataError
from bot.google_sheets.sheets import GoogleSheet
from bot.utilities import (
    cancel_markup,
    catch_exception,
    clean_chat_data,
    db_execute,
    message_logger,
    reply_message,
    send_message,
    Student,
)

FEEl, SLEEP, PULSE = range(3)


@catch_exception
def send_feeling(update, context):
    chat_id = update.effective_chat.id
    students = Student()
    students.get_all_students()

    if chat_id != TRAINER_ID:
        if chat_id not in students:
            reply_message(update, 'Ты не зарегистрирован, пройди регистрацию!')
            return ConversationHandler.END

        reply_message(
            update,
            'Отправь отчёт о своём состоянии.\n'
            'Как ты себя сейчас чувствуешь (от 1 до 10) ?',
            cancel_markup,
        )
        context.chat_data['students'] = students
        return FEEl

    reply_message(update, 'Ты тренер, тебе не нужно отправлять отчёты)')
    return ConversationHandler.END


@catch_exception
def get_feeling(update, context):
    context.chat_data['feel'] = update.message.text
    reply_message(update, 'Сколько ты спал? (ч.)', cancel_markup)
    return SLEEP


@catch_exception
def get_sleep_hours(update, context):
    context.chat_data['sleep'] = update.message.text
    reply_message(update, 'Какой у тебя пульс?', cancel_markup)
    return PULSE


@catch_exception
def get_puls(update, context):
    chat_id = update.effective_chat.id

    context.chat_data['pulse'] = update.message.text

    feelings = []
    for name in ('feel', 'sleep', 'pulse'):
        data = context.chat_data.get(name)
        if not data:
            message_logger.exception(f'Отсутствует переменная {name}')
            raise ChatDataError()
        feelings.append(data)

    students = context.chat_data.get('students')
    student = students.get_student(chat_id)

    message = (
        f'Утренний отчёт студента {student.full_name}:\n'
        f'Дата: {dt.now().strftime(DATE_FORMAT)}\n'
        f'Оценка самочувствия: {feelings[0]}\n'
        f'Количество часов сна: {feelings[1]}\n'
        f'Пульс: {feelings[2]}'
    )

    context.chat_data.clear()

    send_message(context, TRAINER_ID, message)
    reply_message(update, 'Отчёт отправлен тренеру!')
    send_message(context, chat_id, message)

    gs = GoogleSheet(SPREADSHEET_ID)
    gs.send_to_table(feelings, student.full_name, 'B')

    db_execute(
        DATABASE,
        (
            'UPDATE students SET is_send_morning = 1 WHERE chat_id = %s',
            (chat_id,),
        ),
    )

    return ConversationHandler.END


@catch_exception
def cancel(update, context):
    send_message(context, update.effective_chat.id, 'Отменено')
    context.chat_data.clear()

    return ConversationHandler.END


@catch_exception
def invalid_feeling(update, _):
    reply_message(update, 'Вводи только соответствующие цифры!')


feeling_handler = ConversationHandler(
    entry_points=[CommandHandler(FEELING_COMMAND, send_feeling)],
    states={
        FEEl: [
            MessageHandler(Filters.regex(r'^([1-9]|10)$'), get_feeling),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
        SLEEP: [
            MessageHandler(
                Filters.regex(r'^\d{1,2}([.,]\d{1,2})?$'), get_sleep_hours
            ),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
        PULSE: [
            MessageHandler(Filters.regex(r'^\d{2,3}$'), get_puls),
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_feeling)],
)
