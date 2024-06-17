import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json

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
        if player.strip() == "":  # Skip blank player names
            continue
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
    result_data = result_df.to_dict(orient='records')

    # Add last updated timestamp
    result_data.append({
        'Player': 'last_updated',
        'Handicap': '',
        'Last Recorded Score Date': datetime.utcnow().isoformat() + 'Z'
    })

    with open('disc_golf_scores.json', 'w') as f:
        json.dump(result_data, f, indent=4)

if __name__ == '__main__':
    process_scores()