"""
Google Sheets service for interacting with Google Sheets API using a Service Account.
"""
from typing import List, Any, Dict
from googleapiclient.discovery import build
from google.oauth2 import service_account
from pathlib import Path
from fastapi import HTTPException
import time
import socket
import os
import json
import base64

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Set socket timeout to 30 seconds
socket.setdefaulttimeout(30)

# Get the directory of the current file (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent
"""
Credentials path resolution (zero ambiguity):
- Always use the absolute path to backend/credentials.json.
"""
CREDENTIALS_FILE = Path("/Users/carly/projects/kindroot/backend/credentials.json")

class GoogleSheetsService:
    def __init__(self, spreadsheet_id: str):
        """
        Initialize the Google Sheets service.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet to interact with
        """
        self.spreadsheet_id = spreadsheet_id
        self.creds = self._get_credentials()
        self.service = build('sheets', 'v4', credentials=self.creds)

    def _get_credentials(self):
        """
        Build credentials for the Service Account key.
        The target Google Sheet must be shared with the service account email as an editor.
        
        Supports two methods:
        1. Environment variable GOOGLE_CREDENTIALS_BASE64 (for production/Render)
        2. Local credentials.json file (for development)
        
        Returns:
            Credentials: Service account credentials
        """
        # Try to get credentials from environment variable first (production)
        credentials_base64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
        if credentials_base64:
            try:
                # Decode base64 and parse JSON
                credentials_json = base64.b64decode(credentials_base64).decode('utf-8')
                credentials_dict = json.loads(credentials_json)
                creds = service_account.Credentials.from_service_account_info(
                    credentials_dict, scopes=SCOPES
                )
                return creds
            except Exception as e:
                raise ValueError(f"Failed to load credentials from GOOGLE_CREDENTIALS_BASE64: {str(e)}")
        
        # Fall back to local file (development)
        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                f"Credentials file not found at {CREDENTIALS_FILE}. "
                "Set GOOGLE_CREDENTIALS_BASE64 environment variable for production."
            )

        creds = service_account.Credentials.from_service_account_file(
            str(CREDENTIALS_FILE), scopes=SCOPES
        )
        return creds
    
    def expand_sheet_columns(self, sheet_name: str, num_columns: int):
        """
        Expand the sheet to have at least num_columns columns.
        
        Args:
            sheet_name: Name of the sheet to expand
            num_columns: Minimum number of columns needed
        """
        try:
            # Get sheet metadata
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            # Find the sheet by name
            sheet_id = None
            current_columns = 0
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    current_columns = sheet['properties']['gridProperties']['columnCount']
                    break
            
            if sheet_id is None:
                raise ValueError(f"Sheet '{sheet_name}' not found")
            
            # Only expand if needed
            if current_columns >= num_columns:
                return
            
            # Expand the sheet
            request = {
                'requests': [{
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet_id,
                            'gridProperties': {
                                'columnCount': num_columns
                            }
                        },
                        'fields': 'gridProperties.columnCount'
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=request
            ).execute()
            
            print(f"Expanded sheet '{sheet_name}' from {current_columns} to {num_columns} columns")
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error expanding sheet: {str(e)}"
            )

    def read_sheet(self, range_name: str) -> List[List[Any]]:
        """
        Read data from a Google Sheet.
        
        Args:
            range_name: The A1 notation of the range to read
            
        Returns:
            List of rows from the sheet
        """
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            return result.get('values', [])
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error reading from Google Sheet: {str(e)}"
            )

    def write_to_sheet(self, range_name: str, values: List[List[Any]]) -> Dict:
        """
        Write data to a Google Sheet.
        
        Args:
            range_name: The A1 notation of the range to write to
            values: List of rows to write to the sheet
            
        Returns:
            The response from the API
        """
        try:
            body = {
                'values': values
            }
            sheet = self.service.spreadsheets()
            result = sheet.values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            return result
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error writing to Google Sheet: {str(e)}"
            )

    def append_to_sheet(self, range_name: str, values: List[List[Any]]) -> Dict:
        """
        Append data to a Google Sheet.
        
        Args:
            range_name: The A1 notation of the range to append to
            values: List of rows to append to the sheet
            
        Returns:
            The response from the API
        """
        try:
            body = {
                'values': values
            }
            sheet = self.service.spreadsheets()
            result = sheet.values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            return result
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error appending to Google Sheet: {str(e)}"
            )

    def get_last_non_empty_in_column(self, sheet_name: str, column_letter: str) -> Any:
        """
        Return the last non-empty cell value from the specified column in the given sheet.
        
        Args:
            sheet_name: The name of the tab (e.g., 'Processed Data')
            column_letter: The column letter (e.g., 'I')
        
        Returns:
            The last non-empty value, or None if the column is empty
        """
        try:
            range_name = f"{sheet_name}!{column_letter}:{column_letter}"
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                majorDimension='COLUMNS'
            ).execute()
            values = result.get('values', [])
            if not values or not values[0]:
                return None
            # Filter out empty strings and None
            column_values = [v for v in values[0] if v not in (None, "")]
            return column_values[-1] if column_values else None
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error reading last value from column {column_letter} on sheet '{sheet_name}': {str(e)}"
            )

    @staticmethod
    def _index_to_column_letter(index: int) -> str:
        """
        Convert 1-based column index to Excel-style column letters (1->A, 27->AA).
        """
        letters = []
        while index > 0:
            index, remainder = divmod(index - 1, 26)
            letters.append(chr(65 + remainder))
        return ''.join(reversed(letters))

    def get_column_letter_by_header(self, sheet_name: str, header_name: str, header_row: int = 1) -> str:
        """
        Find the column letter by matching the header text in the given header row.

        Args:
            sheet_name: Name of the sheet/tab
            header_name: Header text to match (case-insensitive, trimmed)
            header_row: Row number containing headers (default 1)

        Returns:
            The column letter (e.g., 'A', 'J') if found. Raises 404 if not found.
        """
        try:
            range_name = f"{sheet_name}!{header_row}:{header_row}"
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                majorDimension='ROWS'
            ).execute()
            values = result.get('values', [])
            row = values[0] if values else []
            target = (header_name or "").strip().lower()
            for idx, cell in enumerate(row, start=1):
                if (cell or "").strip().lower() == target:
                    return self._index_to_column_letter(idx)
            raise HTTPException(status_code=404, detail=f"Header '{header_name}' not found on sheet '{sheet_name}' row {header_row}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error resolving header '{header_name}' on sheet '{sheet_name}': {str(e)}"
            )

    def get_last_filled_row_index(self, sheet_name: str, column_letter: str) -> int:
        """
        Return the 1-based index of the last non-empty row in the given column.
        Raises 404 if the column is entirely empty.
        """
        try:
            range_name = f"{sheet_name}!{column_letter}:{column_letter}"
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                majorDimension='COLUMNS'
            ).execute()
            values = result.get('values', [])
            if not values or not values[0]:
                raise HTTPException(status_code=404, detail=f"No values found in column {column_letter} on sheet '{sheet_name}'")
            col = values[0]
            # Walk from bottom to top to find last non-empty
            for idx in range(len(col), 0, -1):
                if col[idx - 1] not in (None, ""):
                    return idx
            raise HTTPException(status_code=404, detail=f"No non-empty values found in column {column_letter} on sheet '{sheet_name}'")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error finding last filled row index in column {column_letter} on sheet '{sheet_name}': {str(e)}"
            )

    def get_cell_value(self, sheet_name: str, cell_a1: str) -> Any:
        """
        Return the value of a single cell specified in A1 notation (e.g., 'A5').
        Returns None if the cell is empty or out of range.
        """
        try:
            range_name = f"{sheet_name}!{cell_a1}"
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            values = result.get('values', [])
            if not values or not values[0]:
                return None
            return values[0][0] if values[0] else None
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error reading cell {cell_a1} on sheet '{sheet_name}': {str(e)}"
            )
