import os
import json
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class GoogleSheet:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    service = None

    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.token_path = os.path.join(self.path, 'token.json')
        self.cred_path = os.path.join(self.path, 'credentials.json')
        self.styles_path = os.path.join(self.path, 'sheet_styles.json')
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

        self.service = build('sheets', 'v4', credentials=creds)

    def add_data(self, sheet_range, values):
        data = [{'range': sheet_range, 'values': values}]
        body = {'valueInputOption': 'USER_ENTERED', 'data': data}

        self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body=body
        ).execute()

    def get_data(self, sheet_range):
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=sheet_range)
            .execute()
        )

        return result.get('values')

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
        with open(self.styles_path, 'r', encoding='UTF-8') as f:
            styles = json.load(f)

        num_rows = len(styles['sheets'][0]['data'][0]['rowData'])
        num_cols = len(styles['sheets'][0]['data'][0]['rowData'][0]['values'])

        # Запрос на добавление листа
        requests = [
            {
                'addSheet': {
                    'properties': {
                        'title': sheet_name,
                        'gridProperties': {
                            'rowCount': 100,
                            'columnCount': 26,
                        },
                    }
                }
            }
        ]

        response = (
            self.service.spreadsheets()
            .batchUpdate(
                spreadsheetId=self.spreadsheet_id, body={'requests': requests}
            )
            .execute()
        )

        # Получение ID добавленного листа
        sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']

        # Запрос на добавление таблицы с применением стилей
        requests = [
            {
                'updateCells': {
                    'rows': [],
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

        data = styles['sheets'][0]['data'][0]['rowData']

        for row in data:
            cells = []
            for val in row['values']:
                if 'userEnteredValue' in val:
                    user_entered_value = val['userEnteredValue']
                else:
                    user_entered_value = {}

                cells.append(
                    {
                        'userEnteredValue': user_entered_value,
                        'userEnteredFormat': val['userEnteredFormat'],
                    }
                )

            requests[0]['updateCells']['rows'].append({'values': cells})
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body={'requests': requests}
        ).execute()

        today = datetime.today().date()
        last_day = today + timedelta(weeks=2)
        two_weeks = []

        while today < last_day:
            two_weeks.append(today.strftime('%d.%m.%Y'))
            today += timedelta(days=1)
        sheet_range = sheet_name + '!A2:A15'
        two_weeks = [[date] for date in two_weeks]
        self.add_data(sheet_range, two_weeks)

        return sheet_id
