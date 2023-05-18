import os

import pytz
from dotenv import load_dotenv

PATH = os.path.dirname(os.path.abspath(__file__))

load_dotenv()

TRAINER_ID = int(os.getenv('TRAINER_ID'))
BOT_TOKEN = os.getenv('BOT_TOKEN')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SOCIAL_AUTH_STRAVA_KEY = os.getenv('SOCIAL_AUTH_STRAVA_KEY')
SOCIAL_AUTH_STRAVA_SECRET = os.getenv('SOCIAL_AUTH_STRAVA_SECRET')

DATABASE = os.path.join(PATH, 'database/training.db')
LOGS_PATH = os.path.join(PATH, 'log/logs')

DB_LOGFILE = 'database.log'
MESSAGES_LOGFILE = 'messages.log'
SHEETS_LOGFILE = 'sheets.log'
STRAVA_LOGGER = 'strava.log'
UNKNOWN_LOGFILE = 'unknown.log'

MAX_LOG_FILE_SIZE = 50 * 1024

DOMAIN = '89.191.226.140'
PORT = 8000
LOGIN_URL = f'http://{DOMAIN}:{PORT}/login/strava/'
STRAVA_ACTIVITIES = 'https://www.strava.com/api/v3/athlete/activities'

MOSCOW_TZ = pytz.timezone('Europe/Moscow')
