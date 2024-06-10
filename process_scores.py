import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import json
from dotenv import load_dotenv

# Load environment variables from .env file if needed
load_dotenv()

def fetch_and_process_data():
    # Google Sheets setup
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_path = 'credentials.json'  # Ensure this path matches the workflow
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)

    # Open the Google Sheets (use the exact name of your Google Sheet)
    sheet_name = 'Form Responses'  # Replace with the name of your Google Sheet
    try:
        spreadsheet = client.open(sheet_name)
        print(f"Successfully opened spreadsheet: {spreadsheet.title}")
    except Exception as e:
        print(f"Error opening spreadsheet: {e}")
        return

    try:
        form_responses_sheet = spreadsheet.worksheet('Form Responses')
        overrides_sheet = spreadsheet.worksheet('Overrides')
        processed_sheet = spreadsheet.worksheet('Processed Scores')
        print("Successfully opened all worksheets")
    except Exception as e:
        print(f"Error opening worksheets: {e}")
        return

    # Fetch data from sheets
    form_responses = form_responses_sheet.get_all_records()
    overrides = overrides_sheet.get_all_records()
    
    # Explicitly define expected headers for processed scores to avoid errors
    expected_headers = ['Player Name', 'Date', 'Score', 'Handicap', 'Adjusted Score']
    processed = processed_sheet.get_all_records(expected_headers=expected_headers)

    # Convert to DataFrames
    form_df = pd.DataFrame(form_responses)
    overrides_df = pd.DataFrame(overrides)
    processed_df = pd.DataFrame(processed)

    # Set Player as index
    form_df.set_index('Player Name', inplace=True)
    overrides_df.set_index('Player Name', inplace=True)
    processed_df.set_index('Player Name', inplace=True)

    # Process Overrides and Apply Adjustments
    for index, row in overrides_df.iterrows():
        if row['Adjustment'] == 'Yes':
            # Apply adjustments
            form_df.loc[index] = row

    # Combine form responses and overrides
    combined_df = pd.concat([form_df, overrides_df]).drop_duplicates(subset=['Player Name', 'Date'], keep='last')

    # Calculate handicaps and adjusted scores
    dates = combined_df.columns[2:]  # Assuming first two columns are Player Name and Date

    def calculate_handicap(row):
        scores = row.dropna().tolist()
        num_scores = len(scores)
        
        if num_scores >= 5:
            return np.mean(sorted(scores)[-5:])
        elif num_scores == 4:
            return np.mean(scores)
        elif num_scores == 3:
            return np.mean(scores)
        else:
            return "Not enough scores"

    def calculate_adjusted_score(raw_score, handicap):
        if pd.isna(raw_score):
            return ""
        return raw_score - handicap

    # Calculate handicap for each player
    combined_df['Handicap'] = combined_df.groupby('Player Name')['Score'].transform(lambda x: calculate_handicap(x))

    # Calculate adjusted scores for each date
    for date in dates:
        combined_df[f'Adjusted {date}'] = combined_df.apply(lambda row: calculate_adjusted_score(row[date], row['Handicap']), axis=1)

    # Load existing data if available
    try:
        with open('disc_golf_scores.json', 'r') as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        existing_data = []

    try:
        with open('historical_data.json', 'r') as f:
            existing_historical_data = json.load(f)
    except FileNotFoundError:
        existing_historical_data = {'players': [], 'current_handicaps': [], 'raw_scores': {}, 'handicaps': {}, 'adjusted_scores': {}}

    # Update the processed data JSON
    output_data = combined_df.reset_index().to_dict(orient='records')
    existing_data.extend(output_data)
    with open('disc_golf_scores.json', 'w') as f:
        json.dump(existing_data, f)

    # Additional data for historical tracking
    for player in combined_df.index:
        if player not in existing_historical_data['players']:
            existing_historical_data['players'].append(player)
            existing_historical_data['handicaps'][player] = []
            existing_historical_data['adjusted_scores'][player] = []

        existing_historical_data['handicaps'][player].extend(combined_df.loc[player, 'Handicap'])
        existing_historical_data['adjusted_scores'][player].extend(combined_df.loc[player, [f'Adjusted {date}' for date in dates]])

    with open('historical_data.json', 'w') as f:
        json.dump(existing_historical_data, f)

# Run the function
fetch_and_process_data()