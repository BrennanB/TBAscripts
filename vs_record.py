import os
import requests
import tbapy
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from tqdm import tqdm
from shutil import rmtree
import PIL

TEAM = 3161
load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))

def ensure_folder_exists(folder):
    if os.path.exists(folder):
        rmtree(folder)
    os.makedirs(folder)

def fetch_team_data(team_key):
    team_info = tba.team(team_key)
    team_name = team_info.nickname
    team_colors = get_team_colors(team_key[3:])
    return team_name, team_colors

def get_team_colors(team_number):
    try:
        response = requests.get(f"https://api.frc-colors.com/v1/team/{team_number}")
        if response.ok:
            data = response.json()
            return [data.get('primaryHex', '#FFFFFF'), data.get('secondaryHex', '#000000')]
        else:
            return ['#FFFFFF', '#000000']
    except Exception as e:
        print(f"Failed to fetch team colors: {e}")
        return ['#FFFFFF', '#000000']

def process_matches(years):
    all_time_records = {}
    for year in years:
        matches = tba.team_matches(TEAM, year=year)
        team_records = {}
        for match in tqdm(matches, desc=f"Processing year {year}"):
            process_match(match, team_records, all_time_records)
        save_year_data(team_records, year)
    return all_time_records

def process_match(match, team_records, all_time_records):
    team_key = f'frc{TEAM}'
    result, alliance, opponents = determine_result_and_alliances(match, team_key)
    if result:
        update_records(team_records, match, result, alliance, 'partner')
        update_records(all_time_records, match, result, alliance, 'partner')
        update_records(team_records, match, result, opponents, 'opponent')
        update_records(all_time_records, match, result, opponents, 'opponent')

def determine_result_and_alliances(match, team_key):
    scores = match['alliances']
    if scores['red']['score'] == -1 and scores['blue']['score'] == -1:
        return None, None, None  # Ignore unplayed matches
    alliance = 'blue' if team_key in match['alliances']['blue']['team_keys'] else 'red'
    opponents = 'red' if alliance == 'blue' else 'blue'
    if match['winning_alliance'] == alliance:
        result = 'win'
    elif match['winning_alliance'] == opponents:
        result = 'loss'
    else:
        result = 'tie'
    return result, alliance, opponents

def update_records(records, match, result, side, relation):
    team_key = f'frc{TEAM}'
    teams = [key[3:] for key in match['alliances'][side]['team_keys'] if key != team_key]
    for team in teams:
        if team not in records:
            records[team] = {'Total Matches With': 0, 'Wins With': 0, 'Losses With': 0,
                             'Wins Against': 0, 'Losses Against': 0}
        records[team]['Total Matches With'] += 1
        key_suffix = 'Wins' if result == 'win' else 'Losses'
        postfix = 'With' if relation == 'partner' else 'Against'
        records[team][f'{key_suffix} {postfix}'] += 1

def save_year_data(team_records, year):
    if team_records:
        df_year = pd.DataFrame.from_dict(team_records, orient='index')
        df_year['Delta Against'] = df_year['Wins Against'] - df_year['Losses Against']
        df_year['Delta With'] = df_year['Wins With'] - df_year['Losses With']
        df_year.to_csv(os.path.join('vs records', f'team_records_{year}.csv'), index_label='Team')

def plot_dataframes(df_all):
    df_all['Delta Against'] = df_all['Wins Against'] - df_all['Losses Against']
    df_all['Delta With'] = df_all['Wins With'] - df_all['Losses With']
    plot_dataframe(df_all.sort_values(by='Total Matches With', ascending=False).head(25), "Top 25 Teams by Total Matches With", 'top_25_total_matches.png')
    plot_dataframe(df_all.sort_values(by='Delta Against', ascending=False).head(25), "Top 25 Teams by Delta Against", 'top_25_delta_against.png')
    plot_dataframe(df_all.sort_values(by='Delta Against').head(25), "Bottom 25 Teams by Delta Against", 'bottom_25_delta_against.png')
    plot_dataframe(df_all.sort_values(by='Delta With', ascending=False).head(25), "Top 25 Teams by Delta With", 'top_25_delta_with.png')
    plot_dataframe(df_all.sort_values(by='Delta With').head(25), "Bottom 25 Teams by Delta With", 'bottom_25_delta_with.png')

def plot_dataframe(df, title, filename):
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.axis('off')
    ax.axis('tight')
    tbl = ax.table(cellText=df.values, colLabels=df.columns, loc='center', cellLoc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(12)
    tbl.scale(1.2, 1.2)
    plt.title(title)
    plt.savefig(os.path.join('vs records', filename))

def create_infographic(team_name, team_number, colors, lifetime_wins, lifetime_losses, top_teams):
    font_path = 'C:\\Windows\\Fonts\\GOTHICB.ttf'  # Path to your font file
    font_size_team = 50  # Font size for the team name
    font_size_lifetime = 30  # Font size for the lifetime wins
    font_size_top_teams = 20  # Font size for the top teams information

    if not os.path.exists(font_path):
        print("Font file does not exist. Please check the path.")
        return

    try:
        font_team = ImageFont.truetype(font_path, font_size_team)
        font_lifetime = ImageFont.truetype(font_path, font_size_lifetime)
        font_top_teams = ImageFont.truetype(font_path, font_size_top_teams)
    except IOError as e:
        print(f"Failed to load font: {e}")
        return

    img = Image.new('RGB', (800, 600), color=colors[0])  # Use primary color as the background
    d = ImageDraw.Draw(img)

    # Draw border
    border_color = colors[1]  # Use secondary color as the border color
    border_width = 7
    img_with_border = Image.new('RGB', (img.width + 2 * border_width, img.height + 2 * border_width), color=border_color)
    img_with_border.paste(img, (border_width, border_width))

    d = ImageDraw.Draw(img_with_border)  # Use ImageDraw on the bordered image

    # Draw team number and name with inverted background
    team_text = f"Team {team_number} - {team_name}"
    team_width, team_height = font_team.getsize(team_text)
    team_position = ((img.width - team_width) / 8 + border_width, 10 + border_width)
    team_bg_rect = [team_position[0] - 10, team_position[1] - 10, team_position[0] + team_width + 10, team_position[1] + team_height + 10]
    d.rectangle(team_bg_rect, fill=colors[1])  # Use secondary color for background behind team number and name
    d.text(team_position, team_text, font=font_team, fill=colors[0])  # Use primary color for text

    # Draw lifetime wins and losses with smaller font
    lifetime_text = f"Lifetime Record: {lifetime_wins} - {lifetime_losses}"
    lifetime_width, lifetime_height = font_lifetime.getsize(lifetime_text)
    lifetime_position = ((img.width - lifetime_width) / 8 + border_width, team_height + 30 + border_width)
    d.text(lifetime_position, lifetime_text, font=font_lifetime, fill=colors[1])  # Use secondary color for text

    # Draw top teams information
    top_teams_text = "Shared the field with:\n"
    for i, (team, matches) in enumerate(top_teams.items(), start=1):
        top_teams_text += f"{i}. {team}: {matches} times\n"

    top_teams_width, top_teams_height = font_top_teams.getsize(top_teams_text)
    top_teams_position = (lifetime_position[0], lifetime_position[1] + lifetime_height + 30)
    d.text(top_teams_position, top_teams_text, font=font_top_teams, fill=colors[1])  # Use secondary color for text

    img_with_border.save(os.path.join('vs records', 'summary_infographic.png'))







def main():
    ensure_folder_exists('vs records')
    team_name, team_colors = fetch_team_data(f'frc{TEAM}')
    all_time_records = process_matches(tba.team_years(TEAM))
    df_all = pd.DataFrame.from_dict(all_time_records, orient='index')
    top_teams = df_all['Total Matches With'].nlargest(5).to_dict()
    print("Top 5 Teams:", top_teams)  # Add this line to check top_teams
    lifetime_wins = df_all['Wins With'].sum()
    lifetime_losses = df_all['Losses With'].sum()
    create_infographic(team_name, TEAM, team_colors, lifetime_wins, lifetime_losses, top_teams)
    plot_dataframes(df_all)
    print(f"Done processing for Team {team_name} with colors {team_colors}")

if __name__ == "__main__":
    main()