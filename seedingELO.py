import tbapy
import csv
from tqdm import tqdm
from dotenv import load_dotenv
import os

# Performs pretty trash

load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))

elo_ratings = {}

def calculate_elo_rank(higher_rank_elo, lower_rank_elo, K=32):
    """Calculate the new Elo rankings based on ranks."""
    expected_score_higher = 1 / (1 + 10 ** ((lower_rank_elo - higher_rank_elo) / 400))
    expected_score_lower = 1 / (1 + 10 ** ((higher_rank_elo - lower_rank_elo) / 400))

    new_higher_rank_elo = higher_rank_elo + K * (1 - expected_score_higher)
    new_lower_rank_elo = lower_rank_elo + K * (0 - expected_score_lower)

    return new_higher_rank_elo, new_lower_rank_elo

def calculate_event(key):
    rankings = tba.event_rankings(key)
    # Update Elo ratings based on ranks
    for i, higher_rank_team in enumerate(rankings["rankings"]):
        higher_rank_team_key = higher_rank_team['team_key']

        # Initialize Elo rating for the team if it doesn't exist
        if higher_rank_team_key not in elo_ratings:
            elo_ratings[higher_rank_team_key] = 1500

        for lower_rank_team in rankings["rankings"][i+1:]:
            lower_rank_team_key = lower_rank_team['team_key']

            # Initialize Elo rating for the team if it doesn't exist
            if lower_rank_team_key not in elo_ratings:
                elo_ratings[lower_rank_team_key] = 1500

            # Update Elo ratings based on a "win" for the higher-ranked team
            elo_ratings[higher_rank_team_key], elo_ratings[lower_rank_team_key] = \
                calculate_elo_rank(elo_ratings[higher_rank_team_key], elo_ratings[lower_rank_team_key])

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
            
years = list(range(2007, 2024))

for year in years:
    calculate_year(year)

csv_path = 'updated_elo_ratings.csv'
with open(csv_path, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Team', 'Elo Rating'])
    for team_key, rating in elo_ratings.items():
        writer.writerow([team_key, rating])