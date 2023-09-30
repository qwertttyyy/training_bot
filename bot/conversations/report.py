from datetime import datetime as dt, timedelta
from http import HTTPStatus

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from bot.commands.command_list import REPORT_COMMAND, STRAVA_LOGIN
from bot.config import (
    DATABASE,
    SPREADSHEET_ID,
    STRAVA_ACTIVITIES,
    TRAINER_ID,
    DATE_FORMAT,
)
from bot.google_sheets.sheets import GoogleSheet
from bot.utilities import (
    cancel_button,
    cancel_markup,
    catch_exception,
    clean_chat_data,
    reply_message,
    send_message,
    get_trainings_data,
    get_report_data,
    set_is_send,
    convert_date,
    get_run_activities,
    get_strava_params,
    write_to_chat_data,
    Student,
)

REPORT, SCREENSHOT, STRAVA, DISTANCE, AVG_TEMP, AVG_HEART_RATE = range(6)
NUMBER_REGEX = r'^\d{1,2}([.,]\d{1,2})?$'
TRAINING_PARAMS = [
    'distance',
    'avg_pace',
    'avg_heart_rate',
    'date',
]


@catch_exception
def send_report(update, context):
    chat_id = update.effective_chat.id
    students = Student()
    students.get_all_students()
    if chat_id != TRAINER_ID:
        if chat_id not in students:
            reply_message(update, 'Ты не зарегистрирован, пройди регистрацию!')

            return ConversationHandler.END

        reply_message(
            update,
            'Отправь отчёт после тренировки.\nВведи отчёт: (текст)',
            cancel_markup,
        )
        context.chat_data['screenshots'] = []
        context.chat_data['students'] = students
        return REPORT
    reply_message(update, 'Ты тренер, тебе не нужно отправлять отчёты)')
    return ConversationHandler.END


@catch_exception
def get_report(update, context):
    report = update.message.text
    if report.startswith('/') and not report.startswith('//'):
        invalid_input(update, context)
        return REPORT
    else:
        context.chat_data['report'] = update.message.text
        context.chat_data['date'] = convert_date(dt.today(), DATE_FORMAT)

        buttons = [
            [
                InlineKeyboardButton(
                    'Прикрепить скриншот', callback_data='screen'
                )
            ],
            [
                InlineKeyboardButton(
                    'Отправить только отчёт', callback_data='only_report'
                )
            ],
            [InlineKeyboardButton('Продолжить', callback_data='strava')],
            cancel_button,
        ]

        reply_markup = InlineKeyboardMarkup(buttons)

        reply_message(
            update,
            'Теперь можешь прикрепить один или несколько скриншотов по '
            'очереди или отправить отчёт.\n'
            'Либо нажми "продолжить", чтобы отправить данные из Strava',
            reply_markup,
        )


@catch_exception
def get_screenshot(update, context):
    send_message(
        context,
        update.effective_chat.id,
        'Отправь один скриншот, он будет сохранён',
    )
    return SCREENSHOT


@catch_exception
def save_screenshot(update, context):
    screenshot = InputMediaPhoto(update.message.photo[-1])
    context.chat_data['screenshots'].append(screenshot)
    buttons = [
        [
            InlineKeyboardButton(
                'Добавить ещё скриншот', callback_data='screen'
            )
        ],
        [
            InlineKeyboardButton(
                'Отправить только отчёт', callback_data='only_report'
            )
        ],
        [InlineKeyboardButton('Продолжить', callback_data='strava')],
        cancel_button,
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    reply_message(
        update,
        'Скриншот сохранён.\n'
        'Можешь добавить ещё один или отправить отчёт.\n'
        'Либо нажми "продолжить", чтобы отправить данные из Strava',
        reply_markup,
    )

    return SCREENSHOT


@catch_exception
def strava_choice(update, context):
    buttons = [
        [
            InlineKeyboardButton(
                'Ввести данные вручную', callback_data='strava_input'
            )
        ],
        [
            InlineKeyboardButton(
                'Отправить из приложения Strava', callback_data='strava_app'
            )
        ],
        cancel_button,
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    chat_id = update.effective_chat.id
    student = context.chat_data.get('students').get_student(chat_id)
    access_data = student.get_access_data()

    message = (
        'Теперь ты можешь отправить данные из Strava с помощью ручного ввода, '
        'либо отправить данные из приложения, для этого тебе нужно '
        f'авторизоваться с помощью команды /{STRAVA_LOGIN} '
        f'(сначала нажми "отменить")'
    )

    if access_data:
        message = (
            'Теперь ты можешь отправить данные из Strava с помощью ручного '
            'ввода, либо отправить данные из приложения'
        )

    send_message(
        context,
        update.effective_chat.id,
        message,
        reply_markup,
    )

    return STRAVA


def send_only_report(update, context):
    chat_id = update.effective_chat.id
    students = context.chat_data.get('students')
    student = students.get_student(chat_id)

    report_data = get_report_data(['report', 'date'], context.chat_data)

    message = (
        f'Отчёт после тренировки студента {student.full_name}\n'
        f'Дата: {report_data["date"]}\n'
        f'"{report_data["report"]}"\n'
    )
    send_message(context, TRAINER_ID, message)
    screenshots = context.chat_data.get('screenshots')

    context.chat_data.clear()

    gs = GoogleSheet(SPREADSHEET_ID)
    gs.send_to_table(
        [report_data['report']], student.full_name, 'I', report_data['date']
    )

    set_is_send(DATABASE, 'is_send_evening', 1, chat_id)

    send_message(context, chat_id, 'Отчёт отправлен тренеру!')
    send_message(context, chat_id, message)

    if screenshots:
        context.bot.send_media_group(chat_id=TRAINER_ID, media=screenshots)
        context.bot.send_media_group(chat_id=chat_id, media=screenshots)

    return ConversationHandler.END


@catch_exception
def get_strava_input(update, context):
    chat_id = update.effective_chat.id
    send_message(
        context,
        chat_id,
        'Теперь вводи данные из Strava в указанном формате.\n'
        'Расстояние:\n'
        '(формат 00.00 км)',
        cancel_markup,
    )
    return DISTANCE


@catch_exception
def get_distance(update, context):
    context.chat_data['distance'] = update.message.text
    reply_message(update, 'Средний темп:\n' '(формат 0:00)', cancel_markup)

    return AVG_TEMP


@catch_exception
def get_avg_pace(update, context):
    context.chat_data['avg_pace'] = update.message.text
    reply_message(update, 'Средний пульс:\n' '(формат 111)', cancel_markup)

    return AVG_HEART_RATE


@catch_exception
def get_avg_heart_rate(update, context):
    context.chat_data['avg_heart_rate'] = update.message.text
    send_strava_data(update, context)
    return ConversationHandler.END


@catch_exception
def bad_request_message(context, chat_id):
    send_message(
        context,
        chat_id,
        'Произошла ошибка получения данных из Strava, '
        'попробуй ввести данные вручную ',
    )
    return ConversationHandler.END


@catch_exception
def get_training(update, context):
    chat_id = update.effective_chat.id
    student = context.chat_data.get('students').get_student(chat_id)
    access_data = student.get_access_data()

    if access_data == HTTPStatus.BAD_REQUEST:
        bad_request_message(context, chat_id)

    elif access_data is None:
        send_message(
            context,
            chat_id,
            f'Сначала авторизуйся через Strava с помощью команды /{STRAVA_LOGIN}',
        )
        return ConversationHandler.END
    else:
        access_token = access_data['access_token']
        timestamp_day_ago = (dt.now() - timedelta(days=14)).timestamp()
        params = {'after': int(timestamp_day_ago)}
        strava_data = get_trainings_data(
            STRAVA_ACTIVITIES, access_token, params
        )
        if strava_data == HTTPStatus.BAD_REQUEST:
            bad_request_message(context, chat_id)
        else:
            last_run = get_run_activities(strava_data)[-1]
            if not last_run:
                send_message(context, chat_id, 'Нужные тренировки отсутствуют')
                return ConversationHandler.END

            training_data = get_strava_params(last_run)

            if not training_data:
                send_message(
                    context,
                    chat_id,
                    'Ошибка получения одного из параметров. '
                    'Попробуй ввести данные вручную',
                )
                return STRAVA

            write_to_chat_data(
                TRAINING_PARAMS, training_data, context.chat_data
            )
            send_strava_data(update, context)
            return ConversationHandler.END


@catch_exception
def send_strava_data(update, context):
    chat_id = update.effective_chat.id

    students = context.chat_data.get('students')
    student = students.get_student(chat_id)

    report_data = get_report_data(
        ['distance', 'avg_pace', 'avg_heart_rate', 'report', 'date'],
        context.chat_data,
    )

    message = (
        f'Отчёт после тренировки студента {student.full_name}\n'
        f'Дата: {report_data["date"]}\n'
        f'"{report_data["report"]}"\n'
        f'Расстояние: {report_data["distance"]}\n'
        f'Средний темп: {report_data["avg_pace"]}\n'
        f'Средний пульс: {report_data["avg_heart_rate"]}'
    )
    send_message(context, TRAINER_ID, message)

    screenshots = context.chat_data.get('screenshots')

    context.chat_data.clear()

    if screenshots:
        context.bot.send_media_group(chat_id=TRAINER_ID, media=screenshots)

    data_to_table = [
        report_data[key]
        for key in [
            'distance',
            'avg_pace',
            'avg_heart_rate',
            'report',
        ]
    ]
    gs = GoogleSheet(SPREADSHEET_ID)
    gs.send_to_table(
        data_to_table, student.full_name, 'F', report_data['date']
    )

    set_is_send(DATABASE, 'is_send_evening', 1, chat_id)
    set_is_send(DATABASE, 'is_send_strava', '', chat_id)

    send_message(context, chat_id, 'Отчёт отправлен тренеру!')
    send_message(context, chat_id, message)

    if screenshots:
        context.bot.send_media_group(chat_id=chat_id, media=screenshots)

    return ConversationHandler.END


@catch_exception
def finish(update, context):
    send_message(context, update.effective_chat.id, 'Диалог завершен')

    return ConversationHandler.END


@catch_exception
def invalid_report(update, _):
    reply_message(update, 'Отправь фото!')


@catch_exception
def invalid_input(update, _):
    reply_message(update, 'Некорректные данные.')


@catch_exception
def cancel(update, context):
    send_message(context, update.effective_chat.id, 'Отменено')
    clean_chat_data(context, TRAINING_PARAMS)

    return ConversationHandler.END


report_handler = ConversationHandler(
    entry_points=[CommandHandler(REPORT_COMMAND, send_report)],
    states={
        REPORT: [
            MessageHandler(Filters.text, get_report),
            CallbackQueryHandler(send_only_report, pattern=r'^only_report$'),
            CallbackQueryHandler(strava_choice, pattern=r'^strava$'),
            CallbackQueryHandler(get_screenshot, pattern=r'^screen$'),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
        ],
        SCREENSHOT: [
            MessageHandler(Filters.photo, save_screenshot),
            CallbackQueryHandler(send_only_report, pattern=r'^only_report$'),
            CallbackQueryHandler(get_screenshot, pattern=r'^screen$'),
            CallbackQueryHandler(strava_choice, pattern=r'^strava$'),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
        ],
        STRAVA: [
            CallbackQueryHandler(get_strava_input, pattern=r'^strava_input$'),
            CallbackQueryHandler(get_training, pattern=r'^strava_app$'),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
        ],
        DISTANCE: [
            MessageHandler(Filters.regex(NUMBER_REGEX), get_distance),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
        ],
        AVG_TEMP: [
            MessageHandler(Filters.regex(r'^\d:\d{2}$'), get_avg_pace),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
        ],
        AVG_HEART_RATE: [
            MessageHandler(Filters.regex(r'^\d{2,3}$'), get_avg_heart_rate),
            CallbackQueryHandler(finish, pattern=r'^end$'),
            CallbackQueryHandler(cancel, pattern=r'^cancel$'),
        ],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_input)],
)
