from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
)

from bot.commands import SEND_WORKOUT
from bot.constants import (
    TRAINER_ID,
    DATABASE,
    SPREADSHEET_ID,
    dates_range_regex,
)
from bot.utilities import get_data_db, get_student_name
from google_sheets.sheets import GoogleSheet

START, TABLE = range(2)


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


def workout_from_table(_, context):
    message = (
        'Введи диапазон дат из таблицы из которых отправить '
        'тренировки.\nФормат ввода: 01.02.2023-12.02.2023'
    )
    buttons = [[InlineKeyboardButton('Назад', callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(buttons)
    context.bot.send_message(
        chat_id=TRAINER_ID, text=message, reply_markup=reply_markup
    )
    return TABLE


def send_from_table(update, context):
    gs = GoogleSheet(SPREADSHEET_ID)

    chat_id = context.chat_data['student_id']
    dates_range = update.message.text

    date1, date2 = dates_range.split('-')
    fullname = ' '.join(get_student_name(DATABASE, chat_id))
    dates = gs.get_data(f'{fullname}!A2:A')

    rows = []
    for i in range(len(dates)):
        if dates[i]:
            if date1 in dates[i][0] or date2 in dates[i][0]:
                rows.append(i + 2)
    trainings = gs.get_data(f'{fullname}!E{rows[0]}:E{rows[1]}')

    message = ''
    for training, day in zip(trainings, dates[rows[0] - 2 : rows[1] - 1]):
        if training and day:
            day = day[0][:9].replace(',', '')
            message += f'{day} {training[0]}\n'

    context.bot.send_message(chat_id=chat_id, text=message)
    buttons = [[InlineKeyboardButton('Назад', callback_data='back')]]
    reply_markup = InlineKeyboardMarkup(buttons)
    context.bot.send_message(
        chat_id=TRAINER_ID,
        text='Тренировки отправлены',
        reply_markup=reply_markup,
    )


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
            CallbackQueryHandler(workout_from_table, pattern=r'^table$'),
            CallbackQueryHandler(send_workout),
            MessageHandler(Filters.regex(r''), workout_from_input),
        ],
        TABLE: [
            MessageHandler(Filters.regex(dates_range_regex), send_from_table),
            CallbackQueryHandler(show_students, pattern=r'^back'),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_training)],
)
