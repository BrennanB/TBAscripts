import os
import csv
import tbapy
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from tqdm import tqdm
from shutil import rmtree

TEAM = 771
load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))

def ensure_folder_exists(folder):
    if os.path.exists(folder):
        rmtree(folder)
    os.makedirs(folder)

def determine_result(match, year, alliance):
    scores = match['alliances']
    if scores['red']['score'] == -1 and scores['blue']['score'] == -1:
        return None  # Ignore unplayed matches
    if year != 2015:
        return 'win' if match['winning_alliance'] == alliance else ('loss' if match['winning_alliance'] != alliance and match['alliances']['red']['score'] != -1 else 'tie')
    else:
        if scores['red']['score'] == scores['blue']['score']:
            return 'tie'
        return 'win' if (alliance == 'red' and scores['red']['score'] > scores['blue']['score']) or (alliance == 'blue' and scores['blue']['score'] > scores['red']['score']) else 'loss'

def update_records(records, team, result, relation):
    if team not in records:
        records[team] = {'Total Matches With': 0, 'Wins With': 0, 'Losses With': 0,
                         'Wins Against': 0, 'Losses Against': 0}
    records[team]['Total Matches With'] += 1
    postfix = 'With' if relation == 'partner' else 'Against'
    
    if result == 'win':
        key_suffix = 'Wins'
    elif result == 'loss':
        key_suffix = 'Losses'
    
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
all_time_records = {}

output_folder = 'vs records'
ensure_folder_exists(output_folder)

for year in years:
    team_records = {}
    matches = tba.team_matches(TEAM, year=year)
    for match in tqdm(matches, desc=f"Processing year {year}"):
        team_key = f'frc{TEAM}'
        alliance, opponents = ('blue', 'red') if team_key in match['alliances']['blue']['team_keys'] else ('red', 'blue') if team_key in match['alliances']['red']['team_keys'] else (None, None)
        if not alliance:
            continue

        result = determine_result(match, year, alliance)
        if result is None or result == 'tie':
            continue  # Skip processing this match if it was unplayed or a tie

        partners = [key[3:] for key in match['alliances'][alliance]['team_keys'] if key != team_key]
        opponents_teams = [key[3:] for key in match['alliances'][opponents]['team_keys']]
        
        for partner in partners:
            update_records(team_records, partner, result, 'partner')
            update_records(all_time_records, partner, result, 'partner')
        for opponent in opponents_teams:
            update_records(team_records, opponent, result, 'opponent')
            update_records(all_time_records, opponent, result, 'opponent')

    # Save individual year CSV
    if team_records:
        df_year = pd.DataFrame.from_dict(team_records, orient='index')
        df_year['Delta Against'] = df_year['Wins Against'] - df_year['Losses Against']
        df_year['Delta With'] = df_year['Wins With'] - df_year['Losses With']
        df_year.to_csv(os.path.join(output_folder, f'team_records_{year}.csv'), index_label='Team')

# Aggregate all data and visualize
df_all = pd.DataFrame.from_dict(all_time_records, orient='index')
df_all['Delta Against'] = df_all['Wins Against'] - df_all['Losses Against']
df_all['Delta With'] = df_all['Wins With'] - df_all['Losses With']
df_all.to_csv(os.path.join(output_folder, 'team_records.csv'), index_label='Team')

plot_dataframe(df_all.sort_values(by='Total Matches With', ascending=False).head(25), f"Top 25 Teams by Total Matches With ({TEAM})", os.path.join(output_folder, "vs_record_summary.png"))
plot_dataframe(df_all.sort_values(by='Delta Against', ascending=False).head(25), f"Top 25 Teams by Delta Against ({TEAM})", os.path.join(output_folder, "top_25_delta_against.png"))
plot_dataframe(df_all.sort_values(by='Delta Against').head(25), f"Bottom 25 Teams by Delta Against ({TEAM})", os.path.join(output_folder, "bottom_25_delta_against.png"))
plot_dataframe(df_all.sort_values(by='Delta With', ascending=False).head(25), f"Top 25 Teams by Delta With ({TEAM})", os.path.join(output_folder, "top_25_delta_with.png"))
plot_dataframe(df_all.sort_values(by='Delta With').head(25), f"Bottom 25 Teams by Delta With ({TEAM})", os.path.join(output_folder, "bottom_25_delta_with.png"))

print("Done")
