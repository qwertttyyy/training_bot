from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
)

from bot.commands.command_list import SEND_WORKOUT
from config import (
    TRAINER_ID,
    DATABASE,
    SPREADSHEET_ID,
)
from bot.utilities import get_data_db, get_student_name
from google_sheets.sheets import GoogleSheet

START = 0


def show_students(update, context):
    if update.effective_chat.id == TRAINER_ID:
        execution = ('SELECT chat_id, name, last_name FROM Students',)
        buttons = []
        students = get_data_db(DATABASE, execution)

        for student in students:
            text = f'{student[1]} {student[2]}'
            button = InlineKeyboardButton(text, callback_data=student[0])
            buttons.append([button])

        buttons.append(
            [InlineKeyboardButton('Завершить', callback_data='cancel')]
        )
        reply_markup = InlineKeyboardMarkup(buttons)

        message = context.bot.send_message(
            text="Выбери студента, которому отправить тренировку:",
            chat_id=TRAINER_ID,
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
    context.chat_data['student_id'] = student
    buttons = [
        [
            InlineKeyboardButton(
                'Отправить тренировки из таблицы', callback_data='table'
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Введи тренировку для студента, '
        'либо нажми "отправить из таблицы":',
        reply_markup=reply_markup,
    )
    return START


def send_from_table(update, context):
    gs = GoogleSheet(SPREADSHEET_ID)

    chat_id = context.chat_data['student_id']

    fullname = ' '.join(get_student_name(DATABASE, chat_id))
    today = datetime.today().date()
    days_until_monday = (7 - today.weekday()) % 7
    next_monday = (today + timedelta(days=days_until_monday)).strftime(
        '%d.%m.%Y'
    )

    dates = gs.get_data(f'{fullname}!A2:A')
    monday_row_index = None

    for i in range(len(dates)):
        if dates[i]:
            if next_monday in dates[i][0]:
                monday_row_index = i + 2

    trainings = gs.get_data(
        f'{fullname}!E{monday_row_index}:E{monday_row_index + 7}'
    )

    message = ''
    trainings_dates = zip(
        trainings, dates[monday_row_index - 2 : monday_row_index + 6]
    )

    for training, day in trainings_dates:
        if training and day:
            day = day[0][:9].replace(',', '')
            message += f'{day} {training[0]}\n'

    context.bot.send_message(chat_id=chat_id, text=message)
    context.bot.send_message(
        chat_id=TRAINER_ID,
        text='Тренировки отправлены',
    )
    show_students(update, context)


def workout_from_input(update, context):
    message = f'Вот твоя задача на сегодня:\n' f'{update.message.text}'
    context.bot.send_message(
        chat_id=context.chat_data['student_id'], text=message
    )
    update.message.reply_text(
        'Тренировка отправлена',
    )
    show_students(update, context)


def cancel(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text='Диалог завершен'
    )

    if context.chat_data.get('student_id'):
        del context.chat_data['student_id']

    return ConversationHandler.END


def invalid_training(bot, _):
    bot.message.reply_text(
        'Отправляй текст только когда нужно, либо заверши диалог!\n'
        'Либо неверный формат данных!'
    )


workout_handler = ConversationHandler(
    entry_points=[CommandHandler(SEND_WORKOUT, show_students)],
    states={
        START: [
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
            CallbackQueryHandler(send_from_table, pattern=r'^table$'),
            CallbackQueryHandler(send_workout),
            MessageHandler(Filters.regex(r''), workout_from_input),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_training)],
)
