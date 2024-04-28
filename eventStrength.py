import tbapy
import csv
from tqdm import tqdm
from dotenv import load_dotenv
import os
import statbotics

# Load environment variables and initialize TBA client
load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))
sb = statbotics.Statbotics()

# Function to export team data to CSV
def export_to_csv(team_data, file_name):
    with open(file_name, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Team Number', 'Team Name', 'Normalized EPA', 'Winrate (%)'])
        for team in team_data:
            writer.writerow([
                team['team'],
                team['name'],
                team['norm_epa'],
                "{:.2f}%".format(team['winrate'] * 100)
            ])

# Retrieve and export team data
team_data = sb.get_teams(limit=6000)
export_to_csv(team_data, 'EPA_data.csv')

# Function to get team number from team key
def get_team_number(team_key):
    return int(team_key[3:]) # Removes the first three characters "FRC"

# Retrieve events for the year 2024
events = tba.events(year=2024, keys=True)

# Initialize data for event strength
event_strength_data = []

# Process each event
for event in tqdm(events):
    # Retrieve teams for the event
    event_teams = tba.event_teams(event, keys=True)
    team_epas = []

    # Retrieve normalized EPA for each team
    for team_key in event_teams:
        team_number = get_team_number(team_key)
        for team in team_data:
            if team['team'] == team_number:
                team_epas.append((team_number, team['norm_epa']))
                break

    # Sort teams by EPA
    sorted_teams = sorted(team_epas, key=lambda x: x[1], reverse=True)

    # Extract top teams for Top2, Top4, Top8, Top24
    top2 = sorted_teams[1][1] if len(sorted_teams) > 1 else None
    top4 = sorted_teams[3][1] if len(sorted_teams) > 3 else None
    top8 = sorted_teams[7][1] if len(sorted_teams) > 7 else None
    top24 = sorted_teams[23][1] if len(sorted_teams) > 23 else None

    # Add data to event strength data
    event_strength_data.append([event, top2, top4, top8, top24])

# Export event strength data to CSV
with open('Event_Strength.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['Event Code', 'Top2', 'Top4', 'Top8', 'Top24'])
    writer.writerows(event_strength_data)
