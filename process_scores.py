import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json
from datetime import datetime, timezone

# Define the scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Define the spreadsheet ID and range
SPREADSHEET_ID = '1pIPq4gkc8y08Px6bwh5bPEOv6HngLxw4zOZX355NW3c'  # Replace with your Google Sheets ID
RANGE_NAME = 'Scores!A2:Z'  # Adjust the range as needed to include headers and data

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
        headers = values[0]
        num_columns = len(headers)
        data = [row for row in values[1:]]
        data = [row + [''] * (num_columns - len(row)) for row in data]
        df = pd.DataFrame(data, columns=headers)
        df['Player'] = df['Player'].ffill()
        df = df.melt(id_vars=["Player"], var_name="Date", value_name="Score")
        df["Score"] = pd.to_numeric(df["Score"], errors="coerce")
        return df

def update_ace_pots(df):
    total_score_count = df['Score'].count()
    
    # Load existing ace pot data if available
    ace_pots = []
    try:
        with open('disc_golf_scores.json', 'r') as f:
            ace_pots = json.load(f)
    except FileNotFoundError:
        ace_pots = []

    # Calculate the total remaining scores excluding paid out pots
    remaining_scores = total_score_count
    for pot in ace_pots:
        if not pot['paid_out']:
            remaining_scores -= int(pot['Last Recorded Score Date'].strip('$'))

    # Update ace pots with new scores
    pot_number = len(ace_pots) + 1 if ace_pots else 1
    while remaining_scores > 0:
        current_pot_value = min(remaining_scores, 100)
        ace_pots.append({
            'Player': f'ace_pot_{pot_number}',
            'Handicap': '',
            'Last Recorded Score Date': f'${current_pot_value}',
            'paid_out': False
        })
        remaining_scores -= current_pot_value
        pot_number += 1

    # Save updated ace pot data to JSON
    with open('disc_golf_scores.json', 'w') as f:
        json.dump(ace_pots, f, indent=4)

def process_scores():
    df = fetch_data_from_sheets()
    if df.empty:
        print("No data to process.")
        return

    players = df['Player'].unique()
    result = []

    for player in players:
        if player.strip() == "":  # Skip blank player names
            continue
        player_scores = df[df['Player'] == player].dropna(subset=['Score'])
        scores = player_scores['Score'].tolist()
        handicap = calculate_handicap(scores)
        
        # Ensure to get the most recent non-null score date
        if not player_scores.empty:
            last_recorded_score_date = player_scores.loc[player_scores['Score'].last_valid_index(), 'Date']
        else:
            last_recorded_score_date = None

        formatted_name = format_name(player)

        if handicap is None:
            needed_scores = 3 - len(scores)
            result.append({
                'Player': formatted_name,
                'Handicap': f'Need {needed_scores} score(s)',
                'Last Recorded Score Date': last_recorded_score_date
            })
        else:
            result.append({
                'Player': formatted_name,
                'Handicap': handicap,
                'Last Recorded Score Date': last_recorded_score_date
            })

    result_df = pd.DataFrame(result)
    result_data = result_df.to_dict(orient='records')

    # Add last updated timestamp
    result_data.append({
        'Player': 'last_updated',
        'Handicap': '',
        'Last Recorded Score Date': datetime.now(timezone.utc).isoformat()
    })

    # Update ace pots with new scores
    update_ace_pots(df)

    # Save player data to JSON
    with open('disc_golf_scores.json', 'w') as f:
        json.dump(result_data, f, indent=4)

if __name__ == '__main__':
    process_scores()