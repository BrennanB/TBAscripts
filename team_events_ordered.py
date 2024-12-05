import tbapy
import csv
from dotenv import load_dotenv
import os
from tqdm import tqdm
import time

# Load environment variables and initialize TBA client
load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))

print('Fetching teams')
# Retrieve all teams with retry logic
max_retries = 3
retry_delay = 5  # seconds

for attempt in range(max_retries):
    try:
        teams = tba.teams(year=2025, keys=True)
        print(f'Found {len(teams)} teams')
        break
    except Exception as e:
        if attempt < max_retries - 1:
            print(f'Error fetching teams (attempt {attempt + 1}/{max_retries}): {str(e)}')
            print(f'Retrying in {retry_delay} seconds...')
            time.sleep(retry_delay)
        else:
            print('Failed to fetch teams after all retries')
            raise

# Function to fetch and sort events for a team with retry logic
def get_sorted_events(team_key, year):
    for attempt in range(max_retries):
        try:
            events = tba.team_events(team_key, year=year)
            events.sort(key=lambda x: x['end_date'], reverse=False)
            return [event['key'] for event in events]
        except Exception as e:
            if attempt < max_retries - 1:
                print(f'Error fetching events for {team_key} (attempt {attempt + 1}/{max_retries}): {str(e)}')
                time.sleep(retry_delay)
            else:
                print(f'Failed to fetch events for {team_key} after all retries')
                return []

# Initialize data for CSV file
team_event_data = []

print('Fetching events for each team')
# Iterate through each team and fetch their events
for team_key in tqdm(teams):
    team_number = team_key[3:]  # Extract the team number from the team key
    events = get_sorted_events(team_key, 2025)
    team_event_data.append([team_number] + events[:7])  # Limit to up to 7 events
    time.sleep(0.1)  # Add small delay between requests

# Write data to CSV file
with open('team_events.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    header = ['Team Number'] + [f'Event {i + 1}' for i in range(7)]
    writer.writerow(header)
    writer.writerows(team_event_data)
