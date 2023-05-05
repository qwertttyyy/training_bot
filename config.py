import os

from dotenv import load_dotenv

load_dotenv(dotenv_path='.tenv')

TRAINER_ID = int(os.getenv('TRAINER_ID'))
BOT_TOKEN = os.getenv('BOT_TOKEN')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

PATH = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(PATH, 'database/training.db')

LOGS_PATH = os.path.join(PATH, 'log/logs')

DB_LOGFILE = 'database.log'
MESSAGES_LOGFILE = 'messages.log'
SHEETS_LOGFILE = 'sheets.log'
UNKNOWN_LOGFILE = 'unknown.log'

MAX_LOG_FILE_SIZE = 25 * 1024
