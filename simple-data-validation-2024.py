import os
import pandas as pd
from dotenv import load_dotenv
import tbapy

# Constants
EXPECTED_ENTRIES_PER_MATCH = 6
ONSTAGE_STATUSES = ['StageLeft', 'StageRight', 'CenterStage']
VALID_PARKED_STATUSES = ['Parked', 'None']

# Load environment variables
load_dotenv()
tba_key = os.getenv("TBAKEY")
tba = tbapy.TBA(tba_key)

# Retrieve matches from The Blue Alliance
matches = tba.event_matches('2024mnmi')

# Load the CSV file
df = pd.read_csv("2470_10klakes_data.csv")

# Normalize team numbers in the DataFrame to remove the '.0' and prepend 'frc'
df['Team Number'] = df['Team Number'].apply(lambda x: 'frc' + str(int(x)) if pd.notna(x) else None)

# Drop rows where 'Qualification Match Number' is NaN before converting to int
df = df.dropna(subset=['Qualification Match Number'])
df['Qualification Match Number'] = df['Qualification Match Number'].astype(int)

# Validation and analysis variables
correct_pairings = 0
incorrect_pairings = 0
auto_speaker_differences = []
auto_amp_differences = []
tele_amp_differences = []
tele_speaker_differences = []

# Validate team entries per match and alliance, and compute differences
for match in matches:
    if 'comp_level' in match and match['comp_level'] == 'qm':  # Focus on qualification matches
        match_number = match['match_number']
        for color, alliance in match['alliances'].items():
            teams = alliance['team_keys']
            score_breakdown = match['score_breakdown'][color]

            auto_speaker_note_count = score_breakdown['autoSpeakerNoteCount']
            auto_amp_note_count = score_breakdown['autoAmpNoteCount']
            tele_amp_note_count = score_breakdown['teleopAmpNoteCount']
            tele_speaker_note_count = score_breakdown['teleopSpeakerNoteCount']

            csv_auto_speaker_total = 0
            csv_auto_amp_total = 0
            csv_tele_amp_total = 0
            csv_tele_speaker_total = 0

            valid_alliance = True
            for i, team in enumerate(teams, start=1):
                onstage_key = f'endGameRobot{i}'
                onstage_status = score_breakdown.get(onstage_key)
                team_data = df[(df['Qualification Match Number'] == match_number) & (df['Team Number'] == team)]

                if not team_data.empty:
                    onstage_csv = team_data['Did they get On Stage?'].iloc[0]
                    if (onstage_csv in ['Yes, solo', 'Yes, with another robot'] and onstage_status in ONSTAGE_STATUSES) \
                            or (onstage_csv in ['Did not attempt', 'Tried and Failed'] and onstage_status in VALID_PARKED_STATUSES):
                        correct_pairings += 1
                        csv_auto_speaker_total += team_data['AutoSpeaker'].iloc[0]
                        csv_auto_amp_total += team_data['AutoAmp'].iloc[0]
                        csv_tele_amp_total += team_data['TeleAmp'].iloc[0]
                        csv_tele_speaker_total += team_data['TeleSpeaker'].iloc[0]
                    else:
                        incorrect_pairings += 1
                        valid_alliance = False
                else:
                    valid_alliance = False

            if valid_alliance:
                auto_speaker_differences.append(abs(csv_auto_speaker_total - auto_speaker_note_count))
                auto_amp_differences.append(abs(csv_auto_amp_total - auto_amp_note_count))
                tele_amp_differences.append(abs(csv_tele_amp_total - tele_amp_note_count))
                tele_speaker_differences.append(abs(csv_tele_speaker_total - tele_speaker_note_count))

# Summary of results and average differences
print(f"Total correct pairings: {correct_pairings}")
print(f"Total incorrect pairings: {incorrect_pairings}")
if auto_speaker_differences:
    print(f"Average AutoSpeaker difference: {sum(auto_speaker_differences) / len(auto_speaker_differences):.2f}")
if auto_amp_differences:
    print(f"Average AutoAmp difference: {sum(auto_amp_differences) / len(auto_amp_differences):.2f}")
if tele_amp_differences:
    print(f"Average TeleAmp difference: {sum(tele_amp_differences) / len(tele_amp_differences):.2f}")
if tele_speaker_differences:
    print(f"Average TeleSpeaker difference: {sum(tele_speaker_differences) / len(tele_speaker_differences):.2f}")

print(len(auto_speaker_differences))
