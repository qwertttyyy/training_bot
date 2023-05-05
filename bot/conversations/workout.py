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
from bot.utilities import (
    get_data_db,
    get_student_name,
    send_message,
    reply_message,
    except_function,
)
from google_sheets.sheets import GoogleSheet

START = 0


@except_function
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

        send_message(
            context,
            TRAINER_ID,
            "Выбери студента, которому отправить тренировку:",
            reply_markup,
        )

        return START
    else:
        reply_message(update, 'Только тренер может использовать эту команду.')

        return ConversationHandler.END


@except_function
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
    send_message(
        context,
        update.effective_chat.id,
        'Введи тренировку для студента, либо нажми "Отправить из таблицы":',
        reply_markup,
    )
    return START


@except_function
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

    if not trainings or len(trainings) < 7:
        message = (
            'Таблица не заполнена!\n'
            'Сначала заполни всю неделю в поле '
            '"Задача" и отправь команду заново.'
        )
        send_message(context, update.effective_chat.id, message)
        return ConversationHandler.END

    message = ''
    trainings_dates = zip(
        trainings, dates[monday_row_index - 2 : monday_row_index + 6]
    )

    for training, day in trainings_dates:
        if training and day:
            day = day[0][:9].replace(',', '')
            message += f'{day} {training[0]}\n'

    send_message(context, chat_id, message)
    send_message(
        context,
        TRAINER_ID,
        'Тренировки отправлены',
    )

    show_students(update, context)


@except_function
def workout_from_input(update, context):
    message = f'Вот твоя задача на сегодня:\n' f'{update.message.text}'
    send_message(context, context.chat_data['student_id'], message)
    reply_message(
        update,
        'Тренировка отправлена',
    )
    show_students(update, context)


@except_function
def cancel(update, context):
    send_message(context, update.effective_chat.id, 'Диалог завершен')

    if context.chat_data.get('student_id'):
        del context.chat_data['student_id']

    return ConversationHandler.END


@except_function
def invalid_training(update, _):
    reply_message(
        update,
        'Отправляй текст только когда нужно, либо заверши диалог!\n'
        'Либо неверный формат данных!',
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
