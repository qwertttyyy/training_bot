from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
)

from bot.commands import UPDATE_WORKOUT
from bot.constants import TRAINER_ID, DATABASE
from bot.utilities import get_data_db

START = 1


def show_students(update, context):
    # TODO: Сделать отправку тренировки из таблицы
    #
    if update.effective_chat.id == TRAINER_ID:
        # create_workout_table = (
        #     '''CREATE TABLE IF NOT EXISTS Workouts (
        #            id INTEGER PRIMARY KEY AUTOINCREMENT,
        #            chat_id INTEGER NOT NULL
        #     );''',
        # )
        # db_execute(DATABASE, create_workout_table)
        execution = (
            ('SELECT chat_id, name, last_name FROM Students',)
        )
        buttons = []
        students = get_data_db(DATABASE, execution)
        for student in students:
            text = f'{student[1]} {student[2]}'
            button = InlineKeyboardButton(text, callback_data=student[0])
            buttons.append([button])

        buttons.append([InlineKeyboardButton('Завершить', callback_data='1')])
        reply_markup = InlineKeyboardMarkup(buttons)

        message = update.message.reply_text(
            "Выбери студента, которому отправить тренировку:",
            reply_markup=reply_markup,
        )
        context.chat_data['students_message'] = message.message_id
        return START
    else:
        update.message.reply_text(
            'Только тренер может использовать эту команду.'
        )
        return ConversationHandler.END


def send_workout(update, context):
    student = int(update.callback_query.data)
    # execution = ('INSERT INTO Workouts (chat_id) VALUES (?)', (student,))
    # db_execute(DATABASE, execution)
    context.chat_data['student_id'] = student
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'Введи тренировку для студента:',
    )
    return START


def workout(update, context):
    message = f'Вот твоя задача на сегодня:\n' f'{update.message.text}'
    context.bot.send_message(
        chat_id=context.chat_data['student_id'], text=message
    )
    update.message.reply_text('Тренировка отправлена')
    del context.chat_data['student_id']
    show_students(update, context)


def cancel(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='Диалог завершен'
    )
    return ConversationHandler.END


def invalid_training(bot, _):
    bot.message.reply_text(
        'Отправляй текст только когда нужно, либо заверши диалог!')


workout_handler = ConversationHandler(
    entry_points=[CommandHandler(UPDATE_WORKOUT, show_students)],
    states={
        START: [
            CallbackQueryHandler(cancel, pattern=r'^1$'),
            CallbackQueryHandler(send_workout),
            MessageHandler(Filters.regex(r''), workout),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_training)],
)
