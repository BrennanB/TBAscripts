import tbapy
import csv
from tqdm import tqdm
from dotenv import load_dotenv
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import queue
import threading
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import concurrent.futures
from cachetools import TTLCache, cached
from collections import defaultdict

def log_progress(message):
    """Unified logging function"""
    tqdm.write(f"[{time.strftime('%H:%M:%S')}] {message}")

# Load environment variables and initialize TBA client
load_dotenv()
tba_key = os.getenv("TBAKEY")
if not tba_key:
    raise Exception("TBA API key not found in environment variables")
log_progress(f"Loaded TBA API key: {tba_key[:4]}...")  # Only show first 4 chars for security
tba = tbapy.TBA(tba_key)

# Configure retry strategy
retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=25,
    pool_maxsize=25
)
tba.session.mount("http://", adapter)
tba.session.mount("https://", adapter)

# Define YEARS at the top level
YEARS = [2024, 2023, 2022]

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
    82: 35,
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
    82: 25,
    3: 10,
    1: 0,
    68: 0,
    2: 0,
    5: 0,
    14: 0
}

# Create a queue for CSV writing
results_queue = queue.Queue()

# Add batch processing for API calls
@cached(cache=TTLCache(maxsize=2000, ttl=3600))
def get_team_info(team):
    """Get team info with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            time.sleep(0.02)  # Add small delay to avoid rate limiting
            return tba.team(team)
        except Exception as e:
            if attempt == max_retries - 1:
                tqdm.write(f"Failed to get team info for {team} after {max_retries} attempts: {str(e)}")
                return None
            time.sleep(1 * (attempt + 1))  # Exponential backoff

def safe_api_call(func, *args, **kwargs):
    """Generic function for safe API calls with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            time.sleep(0.02)  # Add small delay to avoid rate limiting
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                tqdm.write(f"Failed API call after {max_retries} attempts: {str(e)}")
                return None
            time.sleep(1 * (attempt + 1))

# Update other API calling functions to use safe_api_call
@cached(cache=TTLCache(maxsize=1000, ttl=3600))
def get_team_events(team, year):
    return safe_api_call(tba.team_events, team, year=year) or []

@cached(cache=TTLCache(maxsize=1000, ttl=3600))
def get_event_district_points(event_key):
    try:
        result = safe_api_call(tba.event_district_points, event_key)
        return result.get('points', {}) if result else {}
    except (KeyError, TypeError, tbapy.TBAError) as e:
        tqdm.write(f"Error getting district points for {event_key}: {str(e)}")
        return {}

@cached(cache=TTLCache(maxsize=1000, ttl=3600))
def get_event_matches(event_key):
    return safe_api_call(tba.event_matches, event_key) or []

@cached(cache=TTLCache(maxsize=1000, ttl=3600))
def get_event_awards(event_key):
    return safe_api_call(tba.event_awards, event_key) or []

@cached(cache=TTLCache(maxsize=1000, ttl=3600))
def get_event_alliances(event_key):
    return safe_api_call(tba.event_alliances, event_key) or []

@cached(cache=TTLCache(maxsize=1000, ttl=3600))
def has_valid_events(team, year):
    """Check if team has any district or regional events in a given year"""
    events = get_team_events(team, year)
    return any(event['event_type'] in [0, 1] for event in events)

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

def csv_writer_thread(filename, header):
    """Separate thread for writing to CSV"""
    log_progress(f"Starting CSV writer thread for {filename}")
    rows_written = 0
    
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        
        while True:
            try:
                result = results_queue.get(timeout=10)
                if result == "DONE":
                    log_progress(f"CSV writer completed. Total rows written: {rows_written}")
                    break
                if result:
                    writer.writerow(result)
                    file.flush()
                    rows_written += 1
                    if rows_written % 100 == 0:  # Log progress every 100 rows
                        log_progress(f"Written {rows_written} rows to CSV")
                results_queue.task_done()
            except queue.Empty:
                log_progress("CSV writer waiting for data...")
                continue
            except Exception as e:
                log_progress(f"Error writing to CSV: {str(e)}")

def get_active_teams():
    """Get active teams with retry logic"""
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            log_progress(f"Attempting to fetch teams (attempt {attempt + 1}/{max_retries})")
            log_progress("Making API call to TBA for active teams...")
            teams = tba.teams(year=2025, keys=True)
            
            if not teams:
                log_progress("Warning: TBA returned an empty team list")
                raise Exception("Received empty team list from TBA")
            
            rookie_teams = len([t for t in teams if t.startswith('frc2024') or t.startswith('frc2025')])
            log_progress(f'Successfully found {len(teams)} active teams ({rookie_teams} rookie teams)')
            log_progress(f'Sample of teams found: {", ".join(sorted(teams)[:5])}...')
            
            # Verify the data looks correct
            if not all(t.startswith('frc') for t in teams):
                log_progress("Warning: Some team keys don't start with 'frc'")
            
            return teams
            
        except requests.exceptions.RequestException as e:
            log_progress(f"Network error while fetching teams: {str(e)}")
            log_progress(f"Request URL: {tba.URL}/teams/{2025}/keys")
            if attempt < max_retries - 1:
                log_progress(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"Failed to fetch teams after {max_retries} attempts: {str(e)}")
                
        except Exception as e:
            log_progress(f"Unexpected error while fetching teams: {str(e)}")
            if attempt < max_retries - 1:
                log_progress(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"Failed to fetch teams after {max_retries} attempts: {str(e)}")
    
    raise Exception("Failed to fetch teams after all retries")

def process_team_batch(teams):
    """Process a batch of teams more efficiently"""
    log_progress(f"Processing batch of {len(teams)} teams...")
    results = []
    event_cache = {}
    
    # Collect all event keys first
    all_event_keys = set()
    team_events_map = {}
    
    for team in tqdm(teams, desc="Collecting team events", leave=False):
        team_events = []
        for year in YEARS:
            year_events = get_team_events(team, year)
            team_events.extend([(event, year) for event in year_events if event['event_type'] in [0, 1]])
        team_events_map[team] = team_events
        all_event_keys.update(event['key'] for event, _ in team_events)
    
    # Batch fetch all event data
    if all_event_keys:
        event_cache = batch_get_event_data(all_event_keys)
    
    # Process teams using cached event data
    log_progress("Processing individual teams...")
    for team in tqdm(teams, desc="Processing teams", leave=False):
        result = process_team_with_cache(team, team_events_map[team], event_cache)
        if result:
            results_queue.put(result)
    
    log_progress(f"Completed batch processing for {len(teams)} teams")
    return results

def process_team_with_cache(team, team_events, event_cache):
    """Process a single team using cached event data"""
    try:
        team_info = get_team_info(team)
        if not team_info:
            log_progress(f"Failed to get info for team {team}")
            return None
            
        team_name = team_info['nickname']
        log_progress(f"Processing team {team} ({team_name})")
        
        # Initialize score tracking
        team_scores = defaultdict(int)  # First two events only
        full_year_scores = defaultdict(int)  # All events
        event_counts = defaultdict(int)  # Track number of events per year
        full_year_event_counts = defaultdict(int)  # Track total events per year
        
        impact_awards = defaultdict(int)
        engineering_awards = defaultdict(int)
        robot_awards = defaultdict(int)
        sustainability_awards = defaultdict(int)
        years_with_participation = set()
        
        # Process events by year, sorting by date
        for year in YEARS:
            year_events = [(event, year) for event, yr in team_events if yr == year]
            # Sort events by end_date
            year_events.sort(key=lambda x: x[0]['end_date'])
            
            # Process only first two events for regular scoring
            for event, _ in year_events[:2]:
                event_key = event['key']
                if event_cache[event_key]:
                    score = process_event_with_cache(
                        team, event, event_cache[event_key],
                        impact_awards, engineering_awards,
                        robot_awards, sustainability_awards, year
                    )
                    team_scores[year] += score
                    event_counts[year] += 1
                    years_with_participation.add(year)
            
            # Process all events for full year average
            for event, _ in year_events:
                event_key = event['key']
                if event_cache[event_key]:
                    score = process_event_with_cache(
                        team, event, event_cache[event_key],
                        impact_awards, engineering_awards,
                        robot_awards, sustainability_awards, year
                    )
                    full_year_scores[year] += score
                    full_year_event_counts[year] += 1
        
        # Calculate averages
        for year in YEARS:
            if event_counts[year] > 0:
                team_scores[year] = team_scores[year] / event_counts[year]
            if full_year_event_counts[year] > 0:
                full_year_scores[year] = full_year_scores[year] / full_year_event_counts[year]
        
        # Calculate total average score from first two events
        total_avg_score = (sum(team_scores[year] for year in years_with_participation) / 
                          len(years_with_participation)) if years_with_participation else 0
        
        # Calculate full year average score
        full_year_avg = (sum(full_year_scores[year] for year in YEARS if full_year_event_counts[year] > 0) / 
                        sum(1 for year in YEARS if full_year_event_counts[year] > 0)) if any(full_year_event_counts.values()) else 0
        
        # Format all numerical values to one decimal place
        return [
            team[3:], team_name, 
            round(total_avg_score, 1),
            round(team_scores[2024], 1), round(team_scores[2023], 1), round(team_scores[2022], 1),
            impact_awards[2024], impact_awards[2023], impact_awards[2022],  # Award counts remain as integers
            engineering_awards[2024], engineering_awards[2023], engineering_awards[2022],
            robot_awards[2024], robot_awards[2023], robot_awards[2022],
            sustainability_awards[2024], sustainability_awards[2023], sustainability_awards[2022],
            round(full_year_avg, 1),
            round(full_year_scores[2024], 1), round(full_year_scores[2023], 1), round(full_year_scores[2022], 1)
        ]
            
    except Exception as e:
        tqdm.write(f"Error processing team {team}: {str(e)}")
        return None

def process_event_with_cache(team, event, event_data, impact_awards, engineering_awards, robot_awards, sustainability_awards, year):
    """Process a single event for a team using cached event data"""
    score = 0
    event_key = event['key']
    
    # Process district points
    event_points = event_data.get('district_points', {})
    if team in event_points:
        score += event_points[team]['alliance_points'] + event_points[team]['qual_points']
    
    # Process matches using cached match data
    matches = event_data.get('matches', [])
    if matches:
        if event['year'] <= 2022:  # single elims
            score += process_matches_single_elim(team, matches)
        else:  # double elims (2023 and later)
            score += process_matches_double_elim(team, matches, event_data.get('alliances', []))
    
    # Process awards using cached award data
    awards = event_data.get('awards', [])
    if awards:
        score += process_awards_with_cache(team, awards, event['event_type'], 
                                         impact_awards, engineering_awards, 
                                         robot_awards, sustainability_awards, year)
    
    return score

def process_matches_single_elim(team, matches):
    """Process matches for single elimination format"""
    score = 0
    comp_level = ["f", "sf", "qf"]
    for current_match in matches:
        if current_match['comp_level'] in comp_level:
            red_alliance = current_match["alliances"]["red"]["team_keys"]
            blue_alliance = current_match["alliances"]["blue"]["team_keys"]

            if current_match['winning_alliance'] == 'red' and team in red_alliance:
                score += 5
            elif current_match['winning_alliance'] == 'blue' and team in blue_alliance:
                score += 5
    return score

def process_matches_double_elim(team, matches, alliances):
    """Process matches for double elimination format"""
    score = 0
    comp_level = ["f", "sf"]
    points_per_win = 5
    match_11_teams = []

    for current_match in matches:
        if current_match['comp_level'] in comp_level:
            red_alliance = current_match["alliances"]["red"]["team_keys"]
            blue_alliance = current_match["alliances"]["blue"]["team_keys"]
            
            if current_match['comp_level'] == 'sf' and current_match['set_number'] == 11:
                match_11_teams.extend([
                    current_match["alliances"]["red"]["team_keys"][0],
                    current_match["alliances"]["blue"]["team_keys"][0]
                ])

            if current_match['winning_alliance'] == 'red' and team in red_alliance:
                score += points_per_win
            elif current_match['winning_alliance'] == 'blue' and team in blue_alliance:
                score += points_per_win

    # bonus points to the alliances in upper bracket finals
    if match_11_teams and alliances:
        for alliance in alliances:
            if (match_11_teams[0] in alliance['picks'] or 
                match_11_teams[1] in alliance['picks']):
                if team in alliance['picks']:
                    score += points_per_win
    
    return score

def process_awards_with_cache(team, awards, event_type, impact_awards, engineering_awards, robot_awards, sustainability_awards, year):
    """Process awards using cached award data"""
    score = 0
    
    for award in awards:
        for recipient in award['recipient_list']:
            if recipient['team_key'] == team:
                if award['award_type'] == 0:
                    impact_awards[year] += 1
                elif award['award_type'] == 9:
                    engineering_awards[year] += 1
                elif award['award_type'] in [20, 71, 17, 29, 16, 21]:
                    robot_awards[year] += 1
                elif award['award_type'] == 82:
                    sustainability_awards[year] += 1
                score += score_award(award['award_type'], event_type)
    
    return score

# Batch API calls for events
def batch_get_event_data(event_keys):
    """Batch fetch event data to reduce API calls"""
    log_progress(f"Fetching data for {len(event_keys)} events...")
    event_data = defaultdict(dict)
    
    # Parallel fetch of different data types
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        log_progress("Starting parallel data fetch...")
        # Create futures for different types of data
        futures = {
            'district_points': {event_key: executor.submit(get_event_district_points, event_key) 
                              for event_key in event_keys},
            'matches': {event_key: executor.submit(get_event_matches, event_key) 
                       for event_key in event_keys},
            'awards': {event_key: executor.submit(get_event_awards, event_key) 
                      for event_key in event_keys},
            'alliances': {event_key: executor.submit(get_event_alliances, event_key) 
                         for event_key in event_keys}
        }
        
        # Collect results with progress tracking
        for data_type, future_dict in futures.items():
            log_progress(f"Processing {data_type} data...")
            for event_key, future in tqdm(future_dict.items(), 
                                        desc=f"Fetching {data_type}",
                                        leave=False):
                try:
                    event_data[event_key][data_type] = future.result()
                except Exception as e:
                    log_progress(f"Error fetching {data_type} for {event_key}: {str(e)}")
                    event_data[event_key][data_type] = None
    
    log_progress("Completed event data fetch")
    return event_data

def main():
    try:
        log_progress("Starting FFBigData script...")
        
        TEAM_LIST = get_active_teams()
        log_progress(f"Retrieved {len(TEAM_LIST)} active teams")
        
        if not TEAM_LIST:
            raise Exception("Failed to get team list from TBA")
            
        header = ['Team Number', 'Team Name', 'Avg SLFF Points', '2024 Avg SLFF', '2023 Avg SLFF', '2022 Avg SLFF',
                  '2024 Impact', '2023 Impact', '2022 Impact', '2024 EI', '2023 EI', '2022 EI',
                  '2024 Robot', '2023 Robot', '2022 Robot',
                  '2024 Sustainability', '2023 Sustainability', '2022 Sustainability',
                  'Full Year Avg SLFF',  # Add full year average
                  '2024 Full Year Avg', '2023 Full Year Avg', '2022 Full Year Avg']  # Add individual year full averages
        
        log_progress("Starting CSV writer thread...")
        csv_thread = threading.Thread(
            target=csv_writer_thread, 
            args=('BIG DATA.csv', header)
        )
        csv_thread.start()
        
        log_progress("Beginning team processing...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            chunks = [TEAM_LIST[i:i + 50] for i in range(0, len(TEAM_LIST), 50)]
            log_progress(f"Created {len(chunks)} chunks of teams")
            
            list(tqdm(
                executor.map(process_team_batch, chunks),
                total=len(chunks),
                desc="Processing team batches"
            ))
        
        log_progress("Team processing complete, waiting for CSV writer to finish...")
        results_queue.put("DONE")
        csv_thread.join()
        
        log_progress("Script completed successfully!")
        
    except Exception as e:
        log_progress(f"Fatal error in main: {str(e)}")
        raise

if __name__ == "__main__":
    log_progress("Initializing FFBigData script...")
    main()
