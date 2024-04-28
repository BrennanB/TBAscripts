import tbapy
import csv
from dotenv import load_dotenv
import os
from tqdm import tqdm

# Load environment variables and initialize TBA client
load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))

print('Fetching teams')
# Retrieve all teams
teams = tba.teams(year=2024, keys=True)
print(f'Found {len(teams)} teams')

# Function to fetch and sort events for a team
def get_sorted_events(team_key, year):
    events = tba.team_events(team_key, year=year)
    events.sort(key=lambda x: x['end_date'], reverse=False)
    return [event['key'] for event in events]

# Initialize data for CSV file
team_event_data = []

print('Fetching events for each team')
# Iterate through each team and fetch their events
for team_key in tqdm(teams):
    team_number = team_key[3:]  # Extract the team number from the team key
    events = get_sorted_events(team_key, 2024)
    team_event_data.append([team_number] + events[:7])  # Limit to up to 7 events

# Write data to CSV file
with open('team_events.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    header = ['Team Number'] + [f'Event {i + 1}' for i in range(7)]
    writer.writerow(header)
    writer.writerows(team_event_data)
