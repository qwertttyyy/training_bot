import json
import time
from datetime import datetime as dt
from http import HTTPStatus
from typing import Callable

import psycopg2
import requests
from psycopg2._psycopg import cursor
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from bot.config import (
    DATABASE,
    DB_LOGFILE,
    MESSAGES_LOGFILE,
    SOCIAL_AUTH_STRAVA_KEY,
    SOCIAL_AUTH_STRAVA_SECRET,
    STRAVA_LOGGER,
    UNKNOWN_LOGFILE,
    DATE_FORMAT,
)
from bot.exceptions import (
    APIRequestError,
    ChatDataError,
    DatabaseExecutionError,
    DatabaseGetDataError,
    RefreshTokenError,
    ReplyMessageError,
    SendMessageError,
    SendToGoogleSheetsError,
    SheetCreateError,
)
from bot.log.logs_config import setup_logger

db_logger = setup_logger('DATABASE_LOGGER', DB_LOGFILE)
message_logger = setup_logger('MESSAGE_LOGGER', MESSAGES_LOGFILE)
unknown_logger = setup_logger('UNKNOWN_LOGGER', UNKNOWN_LOGFILE)
strava_logger = setup_logger('STRAVA_LOGGER', STRAVA_LOGGER)

EXCEPTIONS = [
    SendToGoogleSheetsError,
    DatabaseExecutionError,
    DatabaseGetDataError,
    SendMessageError,
    ReplyMessageError,
    SheetCreateError,
    ChatDataError,
]

cancel_button = [InlineKeyboardButton('Отменить', callback_data='cancel')]
cancel_markup = InlineKeyboardMarkup([cancel_button])


def db_execute(database: dict, execution: tuple[str] | tuple[str, tuple]):
    try:
        with psycopg2.connect(**database) as conn:
            with conn.cursor() as cur:
                cur.execute(*execution)

        db_logger.info(f'Операция с бд: {execution}')

    except Exception:
        db_logger.exception(f'Ошибка операции с базой {execution}')
        raise DatabaseExecutionError()


def get_data_db(
        database: dict, execution: tuple,
        method: Callable[[cursor], list] = None
):
    try:
        with psycopg2.connect(**database) as conn:
            with conn.cursor() as cur:
                cur.execute(*execution)

                if method is cursor.fetchone:
                    result = cur.fetchone()
                else:
                    result = cur.fetchall()
        db_logger.info(f'Получение данных {result} из бд')
        return result

    except Exception:
        db_logger.exception(f'Ошибка получения данных {execution} из базы')
        raise DatabaseGetDataError()


def get_students_ids(database: dict):
    execution = ('SELECT chat_id FROM students',)
    students_ids = tuple(
        student[0]
        for student in get_data_db(database, execution, method=cursor.fetchall)
    )
    return students_ids


def get_student_name(database: dict, chat_id) -> list[str]:
    get_name = (
        'SELECT name, last_name FROM students WHERE chat_id = %s',
        (chat_id,),
    )
    name = get_data_db(database, get_name, method=cursor.fetchone)

    return name


def set_is_send(database, is_send_var, is_send_value, chat_id):
    db_execute(
        database,
        (
            'UPDATE students SET {} = %s WHERE chat_id = %s'.format(
                is_send_var,
            ),
            (
                is_send_value,
                chat_id,
            ),
        ),
    )


def send_message(context, chat_id, message, reply_markup=None):
    try:
        context.bot.send_message(
            chat_id=chat_id, text=message, reply_markup=reply_markup
        )
        message_logger.info(f'Отправка сообщения {message}')
    except Exception:
        message_logger.exception(
            f'Ошибка отправки сообщения {message} -> {chat_id}'
        )
        raise SendMessageError()


def reply_message(update, message, reply_markup=None):
    try:
        update.message.reply_text(message, reply_markup=reply_markup)
        message_logger.info(f'Ответ сообщением - {message}')
    except Exception:
        message_logger.exception('Ошибка ответа на сообщение.')
        raise ReplyMessageError()


def catch_exception(func):
    def wrapper(update, context):
        try:
            return func(update, context)
        except Exception as e:
            if e.__class__ not in EXCEPTIONS:
                unknown_logger.exception(f'Ошибка: {e}')
            message = (
                'Что-то пошло не так, отправьте команду '
                'заново или свяжитесь с @disinfect2'
            )
            send_message(context, update.effective_chat.id, message)
            return ConversationHandler.END

    return wrapper


def clean_chat_data(context, data_keys):
    for key in data_keys:
        if context.chat_data.get(key):
            del context.chat_data[key]


def refresh_token(extra_data, chat_id):
    current_time = time.time()

    if extra_data['auth_time'] + extra_data['expires'] < current_time:
        url = 'https://www.strava.com/api/v3/oauth/token'
        params = {
            'client_id': SOCIAL_AUTH_STRAVA_KEY,
            'client_secret': SOCIAL_AUTH_STRAVA_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': extra_data['refresh_token'],
        }
        try:
            response = requests.post(url, params=params)
            auth_time = int(time.time())

            if response.status_code in (200, 201):
                response = response.json()
                extra_data['auth_time'] = auth_time
                extra_data['refresh_token'] = response['refresh_token']
                extra_data['expires'] = response['expires_in']
                extra_data['access_token'] = response['access_token']
                str_data = json.dumps(extra_data)
                db_execute(
                    DATABASE,
                    (
                        'UPDATE Students SET tokens = %s WHERE chat_id = %s',
                        (str_data, chat_id),
                    ),
                )
                strava_logger.info(
                    f'Обновлен токен для {chat_id}. {extra_data}'
                )
                return extra_data
            strava_logger.error(
                f'Статус запроса не ОК при обновлении '
                f'токена для {chat_id} - {response.json()}'
            )
            return HTTPStatus.BAD_REQUEST
        except Exception:
            strava_logger.exception(
                f'Ошибка обновления токена для {chat_id} - {extra_data}'
            )
            raise RefreshTokenError()
    return extra_data


def get_access_data(database, chat_id):
    access_data = get_data_db(
        database,
        ('SELECT tokens FROM students WHERE chat_id = %s', (chat_id,)),
        cursor.fetchone,
    )

    if access_data and access_data[0]:
        json_data = json.loads(access_data[0])
        refreshed_data = refresh_token(json_data, chat_id)
        return refreshed_data


def get_training_data(endpoint, access_token, params=None):
    headers = {'Authorization': 'Bearer ' + access_token}
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        if response.status_code in (200, 201):
            strava_logger.info(f'Успешный запрос к api. {response.json()}')
            return response.json()
        strava_logger.error(f'Статус запроса к {endpoint} не ОК. {response}')
        return HTTPStatus.BAD_REQUEST
    except Exception:
        strava_logger.exception(
            f'Ошибка запроса к API. {endpoint} : {params=}'
        )
        raise APIRequestError()


def get_run_activity(strava_data):
    for activity in strava_data:
        if activity['type'] == 'Run':
            return activity


def write_to_chat_data(keys: list | tuple, data: dict, chat_data: dict):
    for key in keys:
        chat_data[key] = data[key]


def get_strava_params(training_data: dict) -> dict | None:
    params = ('distance', 'average_heartrate', 'moving_time', 'start_date')
    obtained_data = {}
    for param in params:
        value = training_data.get(param)
        if not value:
            return None
        obtained_data[param] = value
    result_data = {
        'distance': round(obtained_data['distance'] / 1000, 2),
        'avg_heart_rate': round(obtained_data['average_heartrate']),
        'avg_pace': calculate_pace(
            obtained_data['moving_time'], obtained_data['distance']
        ),
        'date': convert_date(
            obtained_data['start_date'], DATE_FORMAT, '%Y-%m-%dT%H:%M:%SZ'
        ),
    }
    return result_data


def calculate_pace(elapsed_time, distance) -> str:
    pace_decimal = elapsed_time / distance / 60 * 1000
    pace_minute = int(pace_decimal) + pace_decimal % 1 * 60 / 100
    return str(pace_minute)[0:4].replace('.', ':')


def get_report_data(keys: list | tuple, chat_data: dict):
    report_data = {}
    for key in keys:
        data = chat_data.get(key)
        if not data:
            message_logger.exception(f'Отсутствует переменная {key}')
            raise ChatDataError()
        report_data[key] = data

    return report_data


def convert_date(
        date: dt | str, output_format: str, input_format: str | None = None
) -> str:
    if isinstance(date, str):
        return dt.strptime(date, input_format).strftime(output_format)
    return date.strftime(output_format)
