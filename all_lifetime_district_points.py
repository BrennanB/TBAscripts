import tbapy
from dotenv import load_dotenv
import os
from tqdm import tqdm
import csv
import datetime

current_year = datetime.datetime.now().year
years = list(range(2009, current_year + 1))
years.reverse()

print(years)

load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))

teams_data = {}



for year in years:
    districts = tba.districts(year)
    for district in districts:
        rankings = tba.district_rankings(f"{year}{district['abbreviation']}")
        print(f"{year}{district['abbreviation']}")
        for team in tqdm(rankings):
            team_number = team["team_key"][3:]
            team_district_key = f"{team_number}_{district['abbreviation']}"
            if team_district_key not in teams_data:
                teams_data[team_district_key] = {"team": team_number, "district": district['abbreviation'].upper()}
            teams_data[team_district_key][year] = team["point_total"]

# Write to CSV
with open('team_rankings.csv', 'w', newline='') as csvfile:
    fieldnames = ['district', 'team', 'total points', 'average points'] + [str(year) for year in years]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for key, data in teams_data.items():
        total_points = sum(val for k, val in data.items() if isinstance(val, int))
        years_counted = sum(1 for k, val in data.items() if isinstance(val, int))
        average_points = total_points / years_counted if years_counted > 0 else 0
        
        row = {'district': data['district'], 'team': data['team'], 'total points': total_points, 'average points': average_points}
        for year in years:
            row[str(year)] = data.get(year, '')  # Add points if exist for the year, otherwise blank
        
        writer.writerow(row)

print("done")
