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
        # Print fetched values for debugging
        print("Fetched values:")
        for row in values:
            print(row)

        # The first row (index 0) is the header
        headers = values[0]
        num_columns = len(headers)

        # Extract data starting from the row after the header
        data = [row for row in values[1:]]

        # Adjust the number of columns in each data row to match the header
        data = [row + [''] * (num_columns - len(row)) for row in data]

        # Create DataFrame with the correct headers
        df = pd.DataFrame(data, columns=headers)

        # Fill the missing player names in the Player column
        df['Player'] = df['Player'].ffill()

        # Print DataFrame structure for debugging
        print("DataFrame structure:")
        print(df.head())

        # Transpose the data to get it into the right format
        df = df.melt(id_vars=["Player"], var_name="Date", value_name="Score")
        df["Score"] = pd.to_numeric(df["Score"], errors="coerce")
        return df

def format_name(name):
    parts = name.split()
    if len(parts) > 1:
        return f"{parts[0]} {parts[1][0]}."
    return name

def calculate_handicap(scores):
    if len(scores) >= 5:
        return round(sum(scores[-5:]) / 5)
    elif len(scores) == 4:
        return round(sum(scores) / 4)
    elif len(scores) == 3:
        return round(sum(scores) / 3)
    else:
        return None

def process_scores():
    df = fetch_data_from_sheets()
    if df.empty:
        print("No data to process.")
        return

    players = df['Player'].unique()

    result = []

    total_score_count = df['Score'].count()  # Calculate the total count of all scores

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

    # Load existing ace pot data if available
    ace_pots = []
    remaining_scores = total_score_count
    pot_number = 1
    try:
        with open('disc_golf_scores.json', 'r') as f:
            existing_data = json.load(f)
            for entry in existing_data:
                if 'ace_pot' in entry['Player']:
                    if entry['paid_out']:
                        ace_pots.append(entry)
                    else:
                        remaining_scores -= int(entry['Last Recorded Score Date'].strip('$'))
                        ace_pots.append(entry)
    except FileNotFoundError:
        existing_data = []

    # Add new ace pots based on remaining scores
    while remaining_scores > 0:
        current_pot = min(remaining_scores, 100)
        ace_pots.append({
            'Player': f'ace_pot_{pot_number}',
            'Handicap': '',
            'Last Recorded Score Date': f'${current_pot}',
            'paid_out': False  # Mark the new pots as not paid out
        })
        remaining_scores -= current_pot
        pot_number += 1

    # Retain paid_out status for existing ace pots and update values if necessary
    updated_ace_pots = []
    for pot in ace_pots:
        if any(existing_pot['Player'] == pot['Player'] for existing_pot in existing_data):
            existing_pot = next(existing_pot for existing_pot in existing_data if existing_pot['Player'] == pot['Player'])
            if existing_pot['paid_out']:
                updated_ace_pots.append(existing_pot)
            else:
                updated_ace_pots.append(pot)
        else:
            updated_ace_pots.append(pot)

    # Append ace pot data to result
    for pot in updated_ace_pots:
        result_data.append(pot)

    with open('disc_golf_scores.json', 'w') as f:
        json.dump(result_data, f, indent=4)

if __name__ == '__main__':
    process_scores()