import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os
import json

# Define the scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Define the spreadsheet ID and range
SPREADSHEET_ID = '1pIPq4gkc8y08Px6bwh5bPEOv6HngLxw4zOZX355NW3c'  # Replace with your Google Sheets ID
RANGE_NAME = 'Scores!A:Z'  # Adjust the range as needed

def fetch_data_from_sheets():
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return pd.DataFrame()
    else:
        # Transpose the data to get it into the right format
        df = pd.DataFrame(values[1:], columns=values[0])
        df = df.melt(id_vars=["Player"], var_name="Date", value_name="Score")
        df["Score"] = pd.to_numeric(df["Score"], errors="coerce")
        return df

def calculate_handicap(scores):
    if len(scores) >= 5:
        return sum(scores[-5:]) / 5
    elif len(scores) == 4:
        return sum(scores) / 4
    elif len(scores) == 3:
        return sum(scores) / 3
    else:
        return None

def process_scores():
    df = fetch_data_from_sheets()
    if df.empty:
        print("No data to process.")
        return

    players = df['Player'].unique()

    result = []

    for player in players:
        player_scores = df[df['Player'] == player].dropna(subset=['Score'])
        scores = player_scores['Score'].tolist()
        handicap = calculate_handicap(scores)
        last_recorded_score_date = player_scores['Date'].max()

        if handicap is None:
            needed_scores = 3 - len(scores)
            result.append({
                'Player': player,
                'Handicap': f'Not enough scores for handicap, need {needed_scores} more',
                'Last Recorded Score Date': last_recorded_score_date
            })
        else:
            result.append({
                'Player': player,
                'Handicap': handicap,
                'Last Recorded Score Date': last_recorded_score_date
            })

    result_df = pd.DataFrame(result)
    result_df.to_json('disc_golf_scores.json', orient='records')

if __name__ == '__main__':
    process_scores()