import tbapy
import csv
from tqdm import tqdm
from dotenv import load_dotenv
import os

# Function to calculate Elo rank
def calculate_elo_rank(higher_value_elo, lower_value_elo, K=32):
    expected_score_higher = 1 / (1 + 10 ** ((lower_value_elo - higher_value_elo) / 400))
    expected_score_lower = 1 / (1 + 10 ** ((higher_value_elo - lower_value_elo) / 400))

    new_higher_value_elo = higher_value_elo + K * (1 - expected_score_higher)
    new_lower_value_elo = lower_value_elo + K * (0 - expected_score_lower)

    return new_higher_value_elo, new_lower_value_elo

# Load environment variables and initialize TBA client
load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))

# Initialize Elo ratings and RPs data
elo_total_rps = {}
elo_bonus_rps = {}
total_rps_all = {}
bonus_rps_all = {}

def calculate_event(key):
    # Fetch rankings
    rankings = tba.event_rankings(key)
    real_rankings = rankings["rankings"]

    

    # Calculate RPs and bonus RPs for each team
    for team in real_rankings:
        team_key = team["team_key"]
        
        # Initialize Elo rating for the team if it doesn't exist
        if team_key not in elo_total_rps:
            elo_total_rps[team_key] = 1500
        if team_key not in elo_bonus_rps:
            elo_bonus_rps[team_key] = 1500

        total_rps = int(team["sort_orders"][0]*team["matches_played"])
        win_rps = team['record']['wins']*2
        bonus_rps = int(round(total_rps - win_rps,0))
        
        bonus_rps_all[team["team_key"]] = bonus_rps
        total_rps_all[team["team_key"]] = total_rps

    # Compare teams and update Elo ratings
    for team1_key, team1_rps in total_rps_all.items():
        for team2_key, team2_rps in total_rps_all.items():
            if team1_key != team2_key:
                if team1_rps > team2_rps:
                    elo_total_rps[team1_key], elo_total_rps[team2_key] = \
                        calculate_elo_rank(elo_total_rps[team1_key], elo_total_rps[team2_key])
                if bonus_rps_all[team1_key] > bonus_rps_all[team2_key]:
                    elo_bonus_rps[team1_key], elo_bonus_rps[team2_key] = \
                        calculate_elo_rank(elo_bonus_rps[team1_key], elo_bonus_rps[team2_key])

def calculate_year(year):                  
    events = tba.events(year, simple=True)
    events.sort(key=lambda x: x['end_date'], reverse=False)
    for event in tqdm(events, desc="Processing Events"):
        if event['event_type'] == 99 or event['event_type'] == 100:
            pass
        else:
            try:
                calculate_event(event['key'])
                tqdm.write(f"{event['key']} {event['event_type']}") 
            except:
                tqdm.write(f"Error {event['key']} {event['event_type']}")

calculate_year(2023)

# Save the Elo ratings to CSV files
with open('elo_total_rps.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Team', 'Elo Rating for Total RPs'])
    for team_key, rating in elo_total_rps.items():
        writer.writerow([team_key, rating])

with open('elo_bonus_rps.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Team', 'Elo Rating for Bonus RPs'])
    for team_key, rating in elo_bonus_rps.items():
        writer.writerow([team_key, rating])
