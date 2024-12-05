import tbapy
import csv
from tqdm import tqdm
from dotenv import load_dotenv
import os
import pandas as pd

# Load environment variables and initialize TBA client
load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))

def load_year_data(filename):
    try:
        df = pd.read_csv(filename)
        # Use 'num' column as team numbers and set as index
        df['num'] = df['num'].astype(int)
        df.set_index('num', inplace=True)
        return df
    except FileNotFoundError:
        print(f"Warning: {filename} not found")
        return pd.DataFrame()

# Load data from all years
df_2024 = load_year_data('2024_insights.csv')
df_2023 = load_year_data('2023_insights.csv')
df_2022 = load_year_data('2022_insights.csv')

# Calculate weighted EPA
def calculate_weighted_epa(team_number):
    epa_2024 = df_2024.loc[team_number, 'norm_epa'] if team_number in df_2024.index else None
    epa_2023 = df_2023.loc[team_number, 'norm_epa'] if team_number in df_2023.index else None
    epa_2022 = df_2022.loc[team_number, 'norm_epa'] if team_number in df_2022.index else None
    
    # Count how many years have data
    weights = []
    epas = []
    
    if epa_2024 is not None:
        weights.append(0.5)
        epas.append(epa_2024)
    if epa_2023 is not None:
        weights.append(0.3)
        epas.append(epa_2023)
    if epa_2022 is not None:
        weights.append(0.2)
        epas.append(epa_2022)
    
    # If no data available, return 0
    if not weights:
        return 0
    
    # Normalize weights to sum to 1
    total_weight = sum(weights)
    normalized_weights = [w/total_weight for w in weights]
    
    # Calculate weighted average
    weighted_epa = sum(epa * weight for epa, weight in zip(epas, normalized_weights))
    return weighted_epa

# Create team data dictionary with weighted EPAs
team_data = {}
all_teams = set(df_2024.index) | set(df_2023.index) | set(df_2022.index)

for team in all_teams:
    weighted_epa = calculate_weighted_epa(team)
    # Get team name from most recent year's data available
    team_name = None
    for df in [df_2024, df_2023, df_2022]:
        if team in df.index:
            team_name = df.loc[team, 'team']
            break
    team_name = team_name if team_name is not None else str(team)
    
    team_data[team] = {
        'team': team,
        'name': team_name,
        'weighted_epa': weighted_epa
    }

# Export weighted EPA data to CSV
def export_to_csv(team_data, file_name):
    with open(file_name, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Team Number', 'Team Name', '2024 EPA', '2023 EPA', '2022 EPA', 'Weighted EPA'])
        for team_info in team_data.values():
            team_num = team_info['team']
            epa_2024 = df_2024.loc[team_num, 'norm_epa'] if team_num in df_2024.index else ''
            epa_2023 = df_2023.loc[team_num, 'norm_epa'] if team_num in df_2023.index else ''
            epa_2022 = df_2022.loc[team_num, 'norm_epa'] if team_num in df_2022.index else ''
            
            writer.writerow([
                team_info['team'],
                team_info['name'],
                epa_2024,
                epa_2023,
                epa_2022,
                team_info['weighted_epa']
            ])

# Function to get team number from team key
def get_team_number(team_key):
    try:
        if team_key.startswith('frc'):
            return int(team_key[3:])  # Removes the first three characters "frc"
        else:
            print(f"Warning: Invalid team key format: {team_key}")
            return None
    except (ValueError, AttributeError) as e:
        print(f"Error processing team key: {team_key}")
        return None

# Retrieve events for the year 2024
events = tba.events(year=2025, keys=True)

# Initialize data for event strength
event_strength_data = []

# Process each event
for event in tqdm(events):
    # Retrieve teams for the event
    event_teams = tba.event_teams(event, keys=True)
    team_epas = []

    # Retrieve weighted EPA for each team
    for team_key in event_teams:
        team_number = get_team_number(team_key)
        if team_number is not None and team_number in team_data:
            team_epas.append((team_number, team_data[team_number]['weighted_epa']))

    # Only process events with valid teams
    if team_epas:
        # Sort teams by EPA
        sorted_teams = sorted(team_epas, key=lambda x: x[1], reverse=True)

        # Extract top teams for Top2, Top4, Top8, Top24, handling cases with fewer teams
        top2 = sorted_teams[1][1] if len(sorted_teams) > 1 else None
        top4 = sorted_teams[3][1] if len(sorted_teams) > 3 else None
        top8 = sorted_teams[7][1] if len(sorted_teams) > 7 else None
        top24 = sorted_teams[23][1] if len(sorted_teams) > 23 else None

        # Add data to event strength data
        event_strength_data.append([event, top2, top4, top8, top24])
    else:
        print(f"Warning: No valid teams found for event {event}")

# Export event strength data to CSV
with open('Event_Strength.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['Event Code', 'Top2', 'Top4', 'Top8', 'Top24'])
    writer.writerows(event_strength_data)

# Export the weighted EPA data
export_to_csv(team_data, 'EPA_data.csv')
