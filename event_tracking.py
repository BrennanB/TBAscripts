import tbapy
from dotenv import load_dotenv
import os
from tqdm import tqdm


load_dotenv()

events = tba.district_events("2024ont")
for event in events:
    print(event['key'])
    event_teams = tba.event_teams(event["key"])
    print(f"Event: {event['key']}, teams: {len(event_teams)}")