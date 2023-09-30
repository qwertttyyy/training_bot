from datetime import datetime as dt

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from bot.commands.command_list import SEND_WORKOUT_COMMAND
from bot.config import SPREADSHEET_ID, TRAINER_ID, DATE_FORMAT
from bot.google_sheets.sheets import GoogleSheet
from bot.utilities import (
    catch_exception,
    reply_message,
    send_message,
    Student,
)

START = 0


@catch_exception
def show_students(update, context):
    if update.effective_chat.id == TRAINER_ID:
        students = Student()
        students.get_all_students()
        buttons = []
        for student in students:
            text = student.full_name
            button = InlineKeyboardButton(text, callback_data=student.chat_id)
            buttons.append([button])

        buttons.append(
            [InlineKeyboardButton('Завершить', callback_data='cancel')]
        )
        reply_markup = InlineKeyboardMarkup(buttons)

        send_message(
            context,
            TRAINER_ID,
            "Выбери студента, которому отправить тренировку:",
            reply_markup,
        )
        context.chat_data['students'] = students
        return START
    else:
        reply_message(update, 'Только тренер может использовать эту команду.')
        return ConversationHandler.END


@catch_exception
def send_workout(update, context):
    student_chat_id = int(update.callback_query.data)
    context.chat_data['student_chat_id'] = student_chat_id
    buttons = [
        [
            InlineKeyboardButton(
                'Отправить тренировки из таблицы', callback_data='table'
            ),
        ],
        [
            InlineKeyboardButton('Отменить', callback_data='cancel'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    send_message(
        context,
        update.effective_chat.id,
        'Введи тренировку для студента, либо нажми "Отправить из таблицы":',
        reply_markup,
    )
    return START


@catch_exception
def send_from_table(update, context):
    student_chat_id = context.chat_data.get('student_chat_id')
    students = context.chat_data.get('students')
    student = students.get_student(student_chat_id)
    gs = GoogleSheet(SPREADSHEET_ID)
    data = gs.get_data(f'{student.full_name}!A:E')[1:]

    message = ''

    for line in data:
        if line:
            today = dt.today().date()
            date = dt.strptime(line[0].split(', ')[1], DATE_FORMAT).date()
            if len(line) == 5 and date >= today:
                day = line[0][:9].replace(',', '')
                training = line[4]
                message += f'{day} {training}\n'

    if not message:
        send_message(
            context,
            update.effective_chat.id,
            'Тренировки с сегодняшнего дня отсутствуют',
        )
        return ConversationHandler.END

    send_message(context, student_chat_id, message)
    send_message(
        context,
        TRAINER_ID,
        'Тренировки отправлены',
    )
    context.chat_data.clear()
    show_students(update, context)


@catch_exception
def workout_from_input(update, context):
    message = f'Вот твоя задача на сегодня:\n' f'{update.message.text}'
    student_chat_id = context.chat_data.get('student_chat_id')
    if student_chat_id is not None:
        send_message(context, student_chat_id, message)
        reply_message(
            update,
            'Тренировка отправлена',
        )
        context.chat_data.clear()
        show_students(update, context)
    else:
        send_message(
            context,
            update.effective_chat.id,
            'Выбери студента либо заверши диалог',
        )
        return START


@catch_exception
def cancel(update, context):
    send_message(context, update.effective_chat.id, 'Диалог завершен')
    context.chat_data.clear()
    return ConversationHandler.END


@catch_exception
def invalid_training(update, _):
    reply_message(
        update,
        'Отправляй текст только когда нужно, либо заверши диалог!\n'
        'Либо неверный формат данных!',
    )


workout_handler = ConversationHandler(
    entry_points=[CommandHandler(SEND_WORKOUT_COMMAND, show_students)],
    states={
        START: [
            CallbackQueryHandler(cancel, pattern=r'^cancel'),
            CallbackQueryHandler(send_from_table, pattern=r'^table$'),
            CallbackQueryHandler(send_workout),
            MessageHandler(Filters.regex(r''), workout_from_input),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_training)],
)
