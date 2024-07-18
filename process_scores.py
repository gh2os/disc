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

def calculate_ace_pots(df, initial_ace_pots, ace_pot_cap=100):
    ace_pots = initial_ace_pots.copy()
    current_pot_value = ace_pots[-1]['Amount'] if ace_pots else 0

    for _ in df['Score'].dropna():
        current_pot_value += 1
        if current_pot_value >= ace_pot_cap:
            ace_pots[-1]['Amount'] = ace_pot_cap
            ace_pots[-1]['Paid Out'] = False
            ace_pots.append({'Amount': 0, 'Paid Out': False, 'Date': ''})
            current_pot_value = 0

    if ace_pots:
        ace_pots[-1]['Amount'] = current_pot_value

    return ace_pots

def process_scores():
    df = fetch_data_from_sheets()
    if df.empty:
        print("No data to process.")
        return

    # Load initial ace pot state from JSON file
    try:
        with open('disc_golf_scores.json', 'r') as f:
            existing_data = json.load(f)
            initial_ace_pots = [entry for entry in existing_data if 'Ace Pot' in entry]
    except FileNotFoundError:
        initial_ace_pots = [{'Ace Pot': 'Ace Pot 1', 'Amount': 0, 'Paid Out': False, 'Date': ''}]

    players = df['Player'].unique()
    ace_pots = calculate_ace_pots(df, initial_ace_pots, ace_pot_cap=100)

    result = []

    for player in players:
        if player.strip() == "":
            continue
        player_scores = df[df['Player'] == player].dropna(subset=['Score'])
        scores = player_scores['Score'].tolist()
        handicap = calculate_handicap(scores)
        
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

    ace_pot_data = [{'Ace Pot': f'Ace Pot {i+1}', 'Amount': pot['Amount'], 'Paid Out': pot['Paid Out'], 'Date': pot['Date']} for i, pot in enumerate(ace_pots)]

    result_df = pd.DataFrame(result)
    result_data = result_df.to_dict(orient='records')

    result_data.append({
        'Player': 'last_updated',
        'Handicap': '',
        'Last Recorded Score Date': datetime.now(timezone.utc).isoformat()
    })

    result_data.extend(ace_pot_data)

    with open('disc_golf_scores.json', 'w') as f:
        json.dump(result_data, f, indent=4)

if __name__ == '__main__':
    process_scores()