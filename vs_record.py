import os
import csv
import tbapy
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from tqdm import tqdm

TEAM = 3543
load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))

def determine_result(match, year, alliance):
    if year != 2015:
        return 'win' if match['winning_alliance'] == alliance else ('loss' if match['winning_alliance'] != alliance and match['alliances']['red']['score'] != -1 else 'tie')
    else:
        scores = match['alliances']
        if scores['red']['score'] == scores['blue']['score']:
            return 'tie'
        return 'win' if (alliance == 'red' and scores['red']['score'] > scores['blue']['score']) or (alliance == 'blue' and scores['blue']['score'] > scores['red']['score']) else 'loss'

def update_records(records, team, result, relation):
    if team not in records:
        records[team] = {'Total Matches With': 0, 'Wins With': 0, 'Losses With': 0, 'Ties With': 0,
                         'Wins Against': 0, 'Losses Against': 0, 'Ties Against': 0}
    records[team]['Total Matches With'] += 1
    postfix = 'With' if relation == 'partner' else 'Against'
    
    if result == 'win':
        key_suffix = 'Wins'
    elif result == 'loss':
        key_suffix = 'Losses'
    else:
        key_suffix = 'Ties'
    
    records[team][f'{key_suffix} {postfix}'] += 1


def plot_dataframe(df, title, filename):
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor('#f5f5f5')
    ax.set_facecolor('#f5f5f5')

    table = ax.table(cellText=df.values,
                     colLabels=df.columns,
                     rowLabels=df.index,
                     cellLoc='center',
                     loc='center',
                     cellColours=[['#e3e3e3'] * len(df.columns) for _ in range(len(df))],
                     rowColours=['#c2c2c2'] * len(df),
                     colColours=['#c2c2c2'] * len(df.columns))

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(df.columns))))

    ax.set_title(title, fontsize=18, fontweight='bold', color='#333333')
    ax.axis('tight')
    ax.axis('off')
    plt.savefig(filename, bbox_inches='tight', dpi=300, facecolor=fig.get_facecolor())

years = tba.team_years(TEAM)
team_records = {}

for year in years:
    matches = tba.team_matches(TEAM, year=year)
    for match in tqdm(matches, desc=f"Processing year {year}"):
        team_key = f'frc{TEAM}'
        alliance, opponents = ('blue', 'red') if team_key in match['alliances']['blue']['team_keys'] else ('red', 'blue') if team_key in match['alliances']['red']['team_keys'] else (None, None)
        if not alliance:
            continue

        partners = [key[3:] for key in match['alliances'][alliance]['team_keys'] if key != team_key]
        opponents_teams = [key[3:] for key in match['alliances'][opponents]['team_keys']]
        result = determine_result(match, year, alliance)

        for partner in partners:
            update_records(team_records, partner, result, 'partner')
        for opponent in opponents_teams:
            update_records(team_records, opponent, result, 'opponent')

df = pd.DataFrame.from_dict(team_records, orient='index')
df['Delta Against'] = df['Wins Against'] - df['Losses Against']

# Save to CSV
df.to_csv('team_records.csv', index_label='Team')

plot_dataframe(df.sort_values(by='Total Matches With', ascending=False).head(25), f"Top 25 Teams by Total Matches With ({TEAM})", "vs_record_summary.png")
plot_dataframe(df.sort_values(by='Delta Against', ascending=False).head(25), f"Top 25 Teams by Delta Against ({TEAM})", "top_25_delta_against.png")
plot_dataframe(df.sort_values(by='Delta Against').head(25), f"Bottom 25 Teams by Delta Against ({TEAM})", "bottom_25_delta_against.png")

print("Done")
