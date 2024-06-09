import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from dotenv import load_dotenv
import pandas as pd

# Load environment variables from .env file
load_dotenv()

def export_historical_data_to_sheet():
    # Google Sheets setup
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)

    # Open the Google Sheet for historical data
    historical_data_sheet = client.open('Your Google Sheet Name').worksheet('Historical Data')

    # Load historical data from JSON files
    with open('historical_data.json', 'r') as f:
        historical_data = json.load(f)

    # Prepare data for export
    historical_records = []
    for player in historical_data['players']:
        player_records = zip(
            historical_data['raw_scores'].get(player, []),
            historical_data['handicaps'].get(player, []),
            historical_data['adjusted_scores'].get(player, [])
        )
        for date, (raw_score, handicap, adjusted_score) in enumerate(player_records):
            historical_records.append([
                player,
                f"Week {date + 1}",  # Adjust as necessary to match your date format
                raw_score,
                handicap,
                adjusted_score
            ])

    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(historical_records, columns=['Player', 'Date', 'Raw Score', 'Handicap', 'Adjusted Score'])

    # Clear existing content in the historical data sheet
    historical_data_sheet.clear()

    # Update sheet with new data
    historical_data_sheet.update([df.columns.values.tolist()] + df.values.tolist())

# Run the function
export_historical_data_to_sheet()