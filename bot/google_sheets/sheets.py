import json
import os
from datetime import datetime as dt
from datetime import timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from bot.config import SHEETS_LOGFILE, SPREADSHEET_ID, DATE_FORMAT
from bot.exceptions import (
    BatchUpdateError,
    GetDataFromSheetError,
    GoogleSheetsAPIError,
    SendToGoogleSheetsError,
    WriteDataToSheetError,
)
from bot.log.logs_config import setup_logger

sheet_logger = setup_logger('SHEET_LOGGER', SHEETS_LOGFILE)


class GoogleSheet:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    service = None

    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.token_path = os.path.join(self.path, 'token.json')
        self.cred_path = os.path.join(self.path, 'credentials.json')
        self.sheet_styles = os.path.join(self.path, 'sheet_style.json')
        self.header_styles = os.path.join(self.path, 'header_style.json')
        creds = None

        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(
                self.token_path, self.SCOPES
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.cred_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        try:
            self.service = build('sheets', 'v4', credentials=creds)
        except Exception:
            sheet_logger.exception('Ошибка подключения к API GoogleSheets')
            raise GoogleSheetsAPIError()

    def batch_update(self, body):
        try:
            response = (
                self.service.spreadsheets()
                .batchUpdate(spreadsheetId=self.spreadsheet_id, body=body)
                .execute()
            )
            sheet_logger.info(
                f'Выполнен batchUpdate с request {body}. '
                f'Response: {response}'
            )
            return response
        except Exception:
            sheet_logger.exception(f'Ошибка метода bathUpdate {body} ')
            raise BatchUpdateError()

    def add_data(self, sheet_range, values):
        data = [{'range': sheet_range, 'values': values}]
        body = {'valueInputOption': 'USER_ENTERED', 'data': data}
        try:
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id, body=body
            ).execute()
            sheet_logger.info(
                f'Данные {data} успешно добавлены в таблицу {sheet_range}'
            )
        except Exception:
            sheet_logger.exception(
                f'Ошибка записи данных {values} в лист {sheet_range}'
            )
            raise WriteDataToSheetError()

    def get_data(self, sheet_range):
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=sheet_range)
                .execute()
            )

            sheet_logger.info(
                f'Получены данные {result} из листа {sheet_range}'
            )

            return result.get('values')
        except Exception:
            sheet_logger.exception(
                f'Ошибка получения данных из листа {sheet_range}'
            )
            raise GetDataFromSheetError()

    def get_styles(self, sheet_range, filepath):
        response = (
            self.service.spreadsheets()
            .get(
                spreadsheetId=self.spreadsheet_id,
                ranges=[sheet_range],
                fields='sheets(data(rowData(values(userEnteredFormat,userEnteredValue))))',
            )
            .execute()
        )

        # Сохранение стилей в файл
        with open(filepath, 'w', encoding='UTF-8') as f:
            json.dump(response, f, ensure_ascii=False)

    def add_sheet(self, sheet_name):
        requests = [
            {
                'addSheet': {
                    'properties': {
                        'title': sheet_name,
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 15,
                        },
                    }
                }
            }
        ]

        response = self.batch_update({'requests': requests})
        sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']

        return sheet_id

    def archive_sheet(self, sheet_name):
        sheet_id = self.add_sheet(sheet_name)

        with open(self.header_styles, 'r', encoding='UTF-8') as f:
            styles = json.load(f)

        requests = [
            {
                'updateCells': {
                    'rows': [styles],
                    'fields': 'userEnteredValue.stringValue,'
                    'userEnteredFormat.numberFormat,'
                    'userEnteredFormat.borders,'
                    'userEnteredFormat.backgroundColor,'
                    'userEnteredFormat.horizontalAlignment,'
                    'userEnteredFormat.verticalAlignment,'
                    'userEnteredFormat.textFormat',
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'startColumnIndex': 0,
                        'endRowIndex': 1,
                        'endColumnIndex': 9,
                    },
                }
            }
        ]

        self.batch_update({'requests': requests})

        return sheet_id

    def new_student_sheet(self, sheet_name):
        # создание нового листа
        sheet_id = self.add_sheet(sheet_name)

        with open(self.sheet_styles, 'r', encoding='UTF-8') as f:
            styles = json.load(f)

        num_rows = len(styles['sheets'][0]['data'][0]['rowData'])
        num_cols = len(styles['sheets'][0]['data'][0]['rowData'][0]['values'])

        # Запрос на добавление таблицы с применением стилей

        data = styles['sheets'][0]['data'][0]['rowData']

        requests = [
            {
                'updateCells': {
                    'rows': data,
                    'fields': 'userEnteredValue.stringValue,'
                    'userEnteredFormat.numberFormat,'
                    'userEnteredFormat.borders,'
                    'userEnteredFormat.backgroundColor,'
                    'userEnteredFormat.horizontalAlignment,'
                    'userEnteredFormat.verticalAlignment,'
                    'userEnteredFormat.textFormat',
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'startColumnIndex': 0,
                        'endRowIndex': num_rows,
                        'endColumnIndex': num_cols,
                    },
                }
            }
        ]

        self.batch_update({'requests': requests})

        today = dt.today().date()
        last_day = today + timedelta(weeks=2)
        two_weeks = []

        while today < last_day:
            two_weeks.append(today.strftime(DATE_FORMAT))
            today += timedelta(days=1)
        sheet_range = sheet_name + '!A2:A15'
        two_weeks = [[date] for date in two_weeks]

        self.add_data(sheet_range, two_weeks)

        sheet_logger.info(f'Создан лист {sheet_name} {sheet_id=}')

        return sheet_id

    def send_to_table(
        self,
        data: list[int] | tuple[int],
        name: str,
        first_column: str,
        event_date=None,
    ):
        try:
            sheet_range = name + '!A2:A'
            table_dates = self.get_data(sheet_range)

            if not event_date:
                event_date = dt.today().date()

            if isinstance(event_date, str):
                event_date = dt.strptime(event_date, DATE_FORMAT).date()

            for column_index in range(1, len(table_dates) + 1):
                table_date = table_dates[column_index - 1]

                if table_date:
                    table_date = dt.strptime(
                        table_date[0].split(', ')[1], DATE_FORMAT
                    ).date()
                    if table_date == event_date:
                        sheet_data = f'{name}!{first_column}{column_index + 1}'
                        self.add_data(sheet_data, [data])
                        break

        except Exception:
            sheet_logger.exception(f'Ошибка записи {data} в таблицу {name}.')
            raise SendToGoogleSheetsError()

    def move_rows_to_another_sheet(
        self, source_sheet_id, target_sheet_id, target_sheet_name
    ):
        values = self.get_data(f'{target_sheet_name}!A2:A')

        length = 1
        if values:
            length = len(values)

        copy_request = {
            "copyPaste": {
                "source": {
                    "sheetId": source_sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": 8,
                    "startColumnIndex": 0,
                    "endColumnIndex": 9,
                },
                "destination": {
                    "sheetId": target_sheet_id,
                    "startRowIndex": length,
                    "endRowIndex": length + 7,
                    "startColumnIndex": 0,
                    "endColumnIndex": 9,
                },
                "pasteType": "PASTE_NORMAL",
                "pasteOrientation": "NORMAL",
            }
        }
        self.batch_update({"requests": [copy_request]})

        # Delete the source range
        delete_request = {
            "deleteRange": {
                "range": {
                    "sheetId": source_sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": 8,
                    "startColumnIndex": 0,
                    "endColumnIndex": 9,
                },
                "shiftDimension": "ROWS",
            }
        }

        self.batch_update({"requests": [delete_request]})


if __name__ == '__main__':
    gs = GoogleSheet(SPREADSHEET_ID)
