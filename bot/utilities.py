import json
import time
from datetime import datetime as dt
from http import HTTPStatus
from typing import Self

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
    TRAINER_ID,
    SPREADSHEET_ID,
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
from bot.google_sheets.sheets import GoogleSheet
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


class Database:
    database = DATABASE

    def execute(self, execution: tuple[str] | tuple[str, tuple]):
        try:
            with psycopg2.connect(**self.database) as conn:
                with conn.cursor() as cur:
                    cur.execute(*execution)

            db_logger.info(f'Операция с бд: {execution}')

        except Exception:
            db_logger.exception(f'Ошибка операции с базой {execution}')
            raise DatabaseExecutionError()

    def get_data(self, execution: tuple, method=None) -> tuple | tuple[tuple]:
        try:
            with psycopg2.connect(**self.database) as conn:
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


class Student:
    db = Database()
    all_students = None

    def __init__(
            self,
            name=None,
            last_name=None,
            chat_id=None,
            sheet_id=None,
            archive_id=None,
            is_send_morning=None,
            is_send_evening=None,
            tokens=None,
            is_send_strava=None,
    ):
        self.name = name
        self.last_name = last_name
        self.chat_id = chat_id
        self.sheet_id = sheet_id
        self.archive_id = archive_id
        self.is_send_morning = is_send_morning
        self.is_send_evening = is_send_evening
        self.tokens = tokens
        self.is_send_strava = is_send_strava
        self.full_name = f'{self.name} {self.last_name}'

    def __contains__(self, item):
        if self.all_students is not None:
            if not item:
                return False
            if isinstance(item, Student):
                item = item.chat_id
            for student in self.all_students:
                if str(item) == str(student.chat_id):
                    return True
            return False
        else:
            raise ValueError('Сначала вызовите метод get_all_students')

    def __iter__(self):
        if self.all_students is None:
            raise ValueError('Сначала вызовите метод get_all_students')
        return iter(self.all_students)

    @classmethod
    def get_all_students(cls) -> list[Self]:
        execution = (
            'SELECT name, last_name, chat_id, sheet_id, archive_id, '
            'is_send_morning, is_send_evening, tokens, is_send_strava '
            'FROM students;',
        )
        cls.all_students = [
            Student(*data) for data in cls.db.get_data(execution)
        ]
        return cls.all_students

    def get_student(self, chat_id):
        if self.all_students is None:
            raise ValueError('Сначала вызовите метод get_all_students')
        for student in self.all_students:
            if student.chat_id == chat_id:
                return student

    def get_access_data(self):
        if self.tokens:
            json_data = json.loads(self.tokens)
            refreshed_data = refresh_token(json_data, self.chat_id)
            return refreshed_data

    def get_sent_trainings(self):
        return [int(_id) for _id in self.is_send_strava.strip().split()]

    def __repr__(self):
        return f'<{self.name} {self.last_name} {self.chat_id}>'


class Training:
    def __init__(self, strava_data: list = None, training_data: dict = None):
        self.strava_data = strava_data
        if strava_data:
            self.trainings = [
                Training(training_data=training_data)
                for training_data in self.strava_data
                if training_data.get('type') == 'Run'
            ]
        self.training_data = training_data
        if training_data:
            self.id = training_data.get('id')
            self.distance = self._get_distance()
            self.avg_heart_rate = self._get_avg_heart_rate()
            self.avg_pace = self._convert_pace_to_string(self._get_avg_pace())
            self.date = self._get_date()

    def _get_param(self, *params: str, func=None):
        params = [self.training_data.get(param) for param in params]
        if None in params:
            return 'нет данных'
        return func(*params)

    def _get_distance(self) -> int:
        return self._get_param('distance', func=lambda x: round(x / 1000, 2))

    def _get_avg_heart_rate(self) -> int:
        return self._get_param('average_heartrate', func=lambda x: round(x))

    def _get_avg_pace(self) -> str:
        return self._get_param(
            'moving_time',
            'distance',
            func=lambda x, y: self._calculate_pace(x, y),
        )

    def _get_date(self):
        return self._get_param(
            'start_date',
            func=lambda x: convert_date(x, DATE_FORMAT, '%Y-%m-%dT%H:%M:%SZ'),
        )

    def __iter__(self):
        return iter(self.trainings)

    def get_avg_params(self):
        if self.strava_data:

            def check_param(param):
                return param if param != 'нет данных' else 0

            self.distance = 0
            self.avg_pace = 0
            self.avg_heart_rate = 0
            pace_count = 0
            heart_rate_count = 0
            for training in self:
                avg_pace = check_param(training._get_avg_pace())
                avg_heart_rate = check_param(training.avg_heart_rate)
                if avg_pace != 0:
                    self.avg_pace += avg_pace
                    pace_count += 1
                if avg_heart_rate != 0:
                    self.avg_heart_rate += avg_heart_rate
                    heart_rate_count += 1
                self.distance += check_param(training.distance)

            def get_avg_param(param, func=None, count=1):
                if param == 0:
                    return 'нет данных'
                if func:
                    return func(
                        param / count,
                    )
                return param

            self.distance = get_avg_param(self.distance)
            if self.distance != 'нет данных':
                self.distance = round(self.distance, 2)
            self.avg_pace = get_avg_param(
                self.avg_pace, self._convert_pace_to_string, pace_count
            )
            self.avg_heart_rate = get_avg_param(
                self.avg_heart_rate, round, heart_rate_count
            )
            return self

    @staticmethod
    def _convert_pace_to_string(pace):
        if pace != 'нет данных':
            pace = str(round(pace, 2))[0:4].replace('.', ':')
            return pace + '0' if len(pace) == 3 else pace
        return pace

    @staticmethod
    def _calculate_pace(elapsed_time, distance) -> float:
        pace_decimal = elapsed_time / distance / 60 * 1000
        pace_minute = int(pace_decimal) + pace_decimal % 1 * 60 / 100
        return pace_minute


def db_execute(database: dict, execution: tuple[str] | tuple[str, tuple]):
    try:
        with psycopg2.connect(**database) as conn:
            with conn.cursor() as cur:
                cur.execute(*execution)

        db_logger.info(f'Операция с бд: {execution}')

    except Exception:
        db_logger.exception(f'Ошибка операции с базой {execution}')
        raise DatabaseExecutionError()


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


def write_training_id(database, training_id, chat_id):
    training_id = ' ' + str(training_id)
    db_execute(
        database,
        (
            'UPDATE students SET is_send_strava = is_send_strava || %s '
            'WHERE chat_id = %s',
            (training_id, chat_id),
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


def write_to_chat_data(keys: list | tuple, data: dict, chat_data: dict):
    for key in keys:
        chat_data[key] = data[key]


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
                        'UPDATE students SET tokens = %s WHERE chat_id = %s',
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


def get_trainings_data(endpoint, access_token, params=None):
    headers = {'Authorization': 'Bearer ' + access_token}
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        if response.status_code in (200, 201):
            strava_logger.info(f'Успешный запрос к api.')
            return response.json()
        strava_logger.error(f'Статус запроса к {endpoint} не ОК. {response}')
        return HTTPStatus.BAD_REQUEST
    except Exception:
        strava_logger.exception(
            f'Ошибка запроса к API. {endpoint} : {params=}'
        )
        raise APIRequestError()


def get_run_activities(strava_data):
    activities = []
    for activity in strava_data:
        if activity['type'] == 'Run':
            activities.append(activity)
    return activities


def get_strava_params(training_data: dict) -> dict:
    return {
        'distance': (lambda x: round(x / 1000, 2) if x else 'нет данных')(
            training_data.get('distance')
        ),
        'avg_heart_rate': (lambda x: round(x) if x else 'нет данных')(
            training_data.get('average_heartrate')
        ),
        'avg_pace': (
            lambda x, y: calculate_pace(x, y) if x and y else 'нет данных'
        )(training_data.get('moving_time'), training_data.get('distance')),
        'date': (
            lambda x: convert_date(x, DATE_FORMAT, '%Y-%m-%dT%H:%M:%SZ')
            if x
            else 'нет данных'
        )(training_data.get('start_date')),
    }


def send_trainings_to_trainer(context, strava_data, student: Student):
    trainings = Training(strava_data=strava_data)
    check_new = False
    for training in trainings:
        if training.id not in student.get_sent_trainings():
            check_new = True
            message = (
                f'Данные последней тренировки студента '
                f'{student.full_name}\n'
                f'Дата: {training.date}\n'
                f'Расстояние: {training.distance}\n'
                f'Средний темп: {training.avg_pace}\n'
                f'Средний пульс: {training.avg_heart_rate}'
            )
            strava_logger.info(
                f'Автоотправка тренировки. '
                f'name: {student.full_name} '
                f'id: {training.id} '
                f'date: {training.date} '
                f'distance: {training.distance} '
                f'avg_pace: {training.avg_pace} '
                f'avg_heart_rate: {training.avg_heart_rate} '
            )
            send_message(context, TRAINER_ID, message)
            send_message(context, student.chat_id, message)
            write_training_id(DATABASE, training.id, student.chat_id)

    return check_new


def convert_pace_to_string(pace):
    pace = str(pace)[0:4].replace('.', ':')
    return pace + '0' if len(pace) == 3 else pace


def calculate_pace(elapsed_time, distance, is_string=True) -> str | int:
    pace_decimal = elapsed_time / distance / 60 * 1000
    pace_minute = int(pace_decimal) + pace_decimal % 1 * 60 / 100
    if is_string:
        return convert_pace_to_string(pace_minute)
    else:
        return pace_minute


def send_avg_params_to_table(strava_data, student: Student):
    averages = Training(strava_data).get_avg_params()
    # trainings = get_run_activities(strava_data)
    # distance = 0
    # heart_rate = 0
    # pace = 0
    #
    # for training in trainings:
    #     distance += training['distance']
    #     heart_rate += training['average_heartrate']
    #     pace += calculate_pace(
    #         training['moving_time'], training['distance'], is_string=False
    #     )
    #
    # count = len(trainings)
    #
    # data_to_table = [
    #     round(distance / 1000, 2),
    #     convert_pace_to_string(pace / count),
    #     round(heart_rate / count),
    # ]
    # date = convert_date(
    #     trainings[0]['start_date'], DATE_FORMAT, '%Y-%m-%dT%H:%M:%SZ'
    # )
    data_to_table = [
        averages.distance,
        averages.avg_pace,
        averages.avg_heart_rate
    ]
    gs = GoogleSheet(SPREADSHEET_ID)
    gs.send_to_table(data_to_table, student.full_name, 'F', averages.date)


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
