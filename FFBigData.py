import tbapy
import csv
from tqdm import tqdm
from dotenv import load_dotenv
import os
import csv

# Load environment variables and initialize TBA client
load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))

CHAMPS_AWARD_VALUES = {
    0: 20,
    69: 90,
    9: 60,
    10: 35,
    15: 20,
    3: 30,
    71: 30,
    17: 30,
    29: 30,
    16: 30,
    21: 30,
    20: 30,
    1: 0,
    68: 0,
    2: 0,
    5: 0,
    14: 0
}

REGULAR_AWARD_VALUES = {
    0: 60,
    9: 45,
    10: 25,
    20: 20,
    15: 15,
    71: 20,
    17: 20,
    29: 20,
    16: 20,
    21: 20,
    3: 10,
    1: 0,
    68: 0,
    2: 0,
    5: 0,
    14: 0
}

def score_award(tba_award, tba_event_type):
    if tba_event_type in [3, 4]:
        if tba_award in CHAMPS_AWARD_VALUES:
            return CHAMPS_AWARD_VALUES[tba_award]
        else:
            return 10
    elif tba_event_type in [0, 1, 2, 5]:
        if tba_award in REGULAR_AWARD_VALUES:
            return REGULAR_AWARD_VALUES[tba_award]
        else:
            return 5
    return 0

TEAM_LIST = tba.teams(keys=True)
print(TEAM_LIST)
YEARS = [2023, 2022]


with open('BIG DATA.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(['Team Number', 'Team Name', 'Avg SLFF Points', '2023 Avg SLFF', '2022 Avg SLFF', 
                     '2023 Impact', '2022 Impact', '2023 EI', '2022 EI', '2023 Robot', '2022 Robot'])
    
    for team in tqdm(TEAM_LIST):
        team_name = tba.team(team)['nickname']
        tqdm.write(team_name)
        team_scores = {year: 0 for year in YEARS}
        impact_awards = {year: 0 for year in YEARS}  # Initialize counters for Impact Awards
        engineering_awards = {year: 0 for year in YEARS}  # Initialize counters for Engineering Inspiration Awards
        robot_awards = {year: 0 for year in YEARS}
        years_with_participation = []
        for year in YEARS:
            events = tba.team_events(team, year=year)
            events.sort(key=lambda x: x['end_date'], reverse=False)
            event_num = 0
            score = 0
            for event in events:
                if event_num < 2:
                    if event['event_type'] in [0, 1]:
                        event_num += 1
                        event_key = event['key']

                        event_points = tba.event_district_points(event['key'])['points']
                        if team in event_points:
                            score += event_points[team]['alliance_points'] + event_points[team]['qual_points']
                        else:
                            # Handle the case where the team is not in the dictionary
                            # For example, you could log a message or set a default score
                            tqdm.write(f"Team {team} not found in event points for event {event_key}")

                        event_matches = tba.event_matches(event_key)
                        
                        if event['year'] <= 2022: # single elims
                            comp_level = ["f", "sf", "qf"]
                            for current_match in event_matches:
                                if current_match['comp_level'] in comp_level:
                                    red_alliance = current_match["alliances"]["red"]["team_keys"]
                                    blue_alliance = current_match["alliances"]["blue"]["team_keys"]

                                    if current_match['winning_alliance'] == 'red':
                                        if team in red_alliance:
                                            score += 5

                                    elif current_match['winning_alliance'] == 'blue':
                                        if team in blue_alliance:
                                            score += 5 
                        else: # double elims
                            comp_level = ["f", "sf"]
                            points_per_win = 5
                            match_11_teams = []

                            for current_match in event_matches:
                                if current_match['comp_level'] in comp_level:
                                    red_alliance = current_match["alliances"]["red"]["team_keys"]
                                    blue_alliance = current_match["alliances"]["blue"]["team_keys"]
                                    if current_match['comp_level'] == 'sf' and current_match['set_number'] == 11:
                                        match_11_teams.append(current_match["alliances"]["red"]["team_keys"][0])
                                        match_11_teams.append(current_match["alliances"]["blue"]["team_keys"][0])

                                    if current_match['winning_alliance'] == 'red':
                                        if team in red_alliance:
                                            score += points_per_win

                                    elif current_match['winning_alliance'] == 'blue':
                                        if team in blue_alliance:
                                            score += points_per_win

                            # bonus points to the alliances in upper bracket finals
                            alliances = tba.event_alliances(event_key)
                            for alliance in alliances:
                                if match_11_teams[0] in alliance['picks'] or match_11_teams[1] in alliance['picks']:
                                    if team in alliance['picks']:
                                        score += points_per_win
                        # AWARDS
                        event_awards = tba.event_awards(event_key)
                        for award in event_awards:
                            award_teams = award['recipient_list']
                            for recipient in award_teams:
                            
                                if recipient['team_key'] == team:
                                    if award['award_type'] == 0:
                                        impact_awards[year] += 1
                                    elif award['award_type'] == 9:
                                        engineering_awards[year] += 1
                                    elif award['award_type'] in [20, 71, 17, 29, 16, 21]:
                                        robot_awards[year] += 1
                                    award_points = score_award(award['award_type'], event['event_type'])
                                    score += int(award_points)
                avg_score = score / event_num if event_num > 0 else 0
                team_scores[year] = avg_score
                years_with_participation.append(year)
            # Get team information
            team_info = tba.team(team)
            team_name = team_info['nickname']
            team_number = team[3:]  # Remove the first three characters from 'team'

            # Calculate overall average SLFF points
            if years_with_participation:
                total_avg_score = sum(team_scores[year] for year in years_with_participation) / len(years_with_participation)
            else:
                total_avg_score = 0

        # Write to CSV
        writer.writerow([team_number, team_name, total_avg_score, 
                         team_scores.get(2023, 0), team_scores.get(2022, 0),
                         impact_awards.get(2023, 0), impact_awards.get(2022, 0),
                         engineering_awards.get(2023, 0), engineering_awards.get(2022, 0),
                         robot_awards.get(2023, 0), robot_awards.get(2022, 0)])
        tqdm.write(f"{team} {score} year {year}")
