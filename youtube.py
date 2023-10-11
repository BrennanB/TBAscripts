import tbapy
from dotenv import load_dotenv
import os
from tqdm import tqdm
import requests
import csv

load_dotenv()
tba = tbapy.TBA(os.getenv("TBAKEY"))
API_KEY_YOUTUBE = os.getenv("YT_API_KEY")

def get_channel_id_from_custom_url(api_key, custom_url):
    base_url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "id",
        "forCustomUrl": custom_url,
        "key": api_key
    }
    
    response = requests.get(base_url, params=params)
    data = response.json()
    
    if "items" in data and len(data["items"]) > 0:
        return data["items"][0]["id"]
    return None


def get_channel_id_from_username(api_key, username):
    base_url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "id",
        "forUsername": username,
        "key": api_key
    }
    
    response = requests.get(base_url, params=params)
    data = response.json()
    print(data)
    
    if "items" in data and len(data["items"]) > 0:
        return data["items"][0]["id"]
    return None


def get_youtube_channel_stats(api_key, channel_id):
    base_url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "snippet,statistics",
        "id": channel_id,
        "key": api_key
    }
    
    response = requests.get(base_url, params=params)
    data = response.json()
    
    if "items" in data and len(data["items"]) > 0:
        item = data["items"][0]
        snippet = item["snippet"]
        statistics = item["statistics"]

        channel_info = {
            "title": snippet["title"],
            "publishedAt": snippet["publishedAt"],
            "subscriberCount": statistics["subscriberCount"],
            "viewCount": statistics["viewCount"],
            "videoCount": statistics["videoCount"]
        }
        return channel_info
    else:
        return None

print("Loading teams")
teams = tba.teams()
print("loaded teams")

# Initialize the CSV file with headers
with open('youtube_channel_stats.csv', 'w', newline='') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(['Team', 'Title', 'Published At', 'Subscriber Count', 'View Count', 'Video Count'])
print("Initialized CSV file")

for team in tqdm(teams):
    team_profile = tba.team_profiles(team.team_number)
    for profile in team_profile:
        if profile.type == "youtube-channel":
            channel_id = get_channel_id_from_username(API_KEY_YOUTUBE, profile.foreign_key)
            if channel_id:  # Ensure we got a channel ID
                result = get_youtube_channel_stats(API_KEY_YOUTUBE, channel_id)
                if result:  # Check if we got valid results
                    # Append the result to the CSV
                    with open('youtube_channel_stats.csv', 'a', newline='') as csv_file:
                        writer = csv.writer(csv_file)
                        writer.writerow([team.team_number, result['title'], result['publishedAt'], result['subscriberCount'], result['viewCount'], result['videoCount']])

# print("Done")
