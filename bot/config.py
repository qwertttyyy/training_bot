import os

import pytz
from dotenv import load_dotenv

load_dotenv()

LOCAL = os.getenv("LOCAL")
print("11111111111", LOCAL)

PATH = os.path.dirname(os.path.abspath(__file__))

TRAINER_ID = int(os.getenv("TRAINER_ID"))
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
SOCIAL_AUTH_STRAVA_KEY = os.getenv("SOCIAL_AUTH_STRAVA_KEY")
SOCIAL_AUTH_STRAVA_SECRET = os.getenv("SOCIAL_AUTH_STRAVA_SECRET")

DATABASE = {
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("POSTGRES_DB"),
}

LOGS_PATH = os.path.join(PATH, "log/logs")
DB_LOGFILE = "database.log"
MESSAGES_LOGFILE = "messages.log"
SHEETS_LOGFILE = "sheets.log"
STRAVA_LOGGER = "strava.log"
UNKNOWN_LOGFILE = "unknown.log"
MAX_LOG_FILE_SIZE = 50 * 1024

DOMAIN = os.getenv("DOMAIN")

if LOCAL:
    LOGIN_URL = f"http://127.0.0.1:8000/login/strava/"
    STRAVA_ACTIVITIES = "https://www.strava.com/api/v3/athlete/activities"
else:
    LOGIN_URL = f"https://{DOMAIN}/login/strava/"
    STRAVA_ACTIVITIES = "https://www.strava.com/api/v3/athlete/activities"

MOSCOW_TZ = pytz.timezone("Europe/Moscow")
DATE_FORMAT = "%d.%m.%Y"
