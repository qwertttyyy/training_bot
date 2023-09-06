import os

import pytz
from dotenv import load_dotenv

load_dotenv()

PATH = os.path.dirname(os.path.abspath(__file__))

TRAINER_ID = int(os.getenv('TRAINER_ID', '1726709711'))
BOT_TOKEN = os.getenv(
    'BOT_TOKEN', '6290773174:AAFZf6xynuXHi3pBd_9gq8SK_q9_Q5fItE4'
)
SPREADSHEET_ID = os.getenv(
    'SPREADSHEET_ID', '1OaaJHLyJOZLAxETUByA1o8AvQKK-Kqb2Mb7mdfeUqnU'
)
SOCIAL_AUTH_STRAVA_KEY = os.getenv('SOCIAL_AUTH_STRAVA_KEY', '105996')
SOCIAL_AUTH_STRAVA_SECRET = os.getenv(
    'SOCIAL_AUTH_STRAVA_SECRET', '309334484db6102a40bd3e6f4d85fc759e917502'
)

DATABASE = {
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'QWEasd135'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'test_django_db'),
}

LOGS_PATH = os.path.join(PATH, 'log/logs')

DB_LOGFILE = 'database.log'
MESSAGES_LOGFILE = 'messages.log'
SHEETS_LOGFILE = 'sheets.log'
STRAVA_LOGGER = 'strava.log'
UNKNOWN_LOGFILE = 'unknown.log'

MAX_LOG_FILE_SIZE = 50 * 1024

PORT = 8000
DOMAIN = 'trainingbot-app.ddns.net'
TEST_DOMAIN = '127.0.0.1'
LOGIN_URL = f'https://{DOMAIN}/login/strava/'

TEST_ACTIVITIES = (
    'https://my-json-server.typicode.com/qwertttyyy/strava/activities2'
)
STRAVA_ACTIVITIES = 'https://www.strava.com/api/v3/athlete/activities'

MOSCOW_TZ = pytz.timezone('Europe/Moscow')
DATE_FORMAT = '%d.%m.%Y'
