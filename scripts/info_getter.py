import requests
from bs4 import BeautifulSoup
import json
import os

# Adjust the paths relative to the script's current location
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, 'ani-tool', 'data')

# Ensure the 'data' directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def extract_anime_name(soup, debug=False):
    """Extract the anime name from the page content."""
    anime_name = "Unknown Anime"
    try:
        series_title_div = soup.find('div', class_='series-title')
        if series_title_div:
            h1_tag = series_title_div.find('h1', itemprop='name')
            if h1_tag:
                span_tag = h1_tag.find('span')
                if span_tag:
                    anime_name = span_tag.get_text(strip=True)
                    if debug:
                        print(f"Extracted anime name: {anime_name}")
    except Exception as e:
        if debug:
            print(f"Error extracting anime name: {e}")
    return anime_name

def check_filme_section(base_url, debug=False):
    """Check if the /filme section exists and fetch its movies."""
    filme_url = base_url + '/filme'
    try:
        response = requests.get(filme_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        movies = soup.find_all('tr', {'itemprop': 'episode'})
        movie_info_list = []
        if movies:
            if debug:
                print(f"/filme section exists and contains {len(movies)} movies.")

            for index, movie in enumerate(movies, 1):
                title_div = movie.find('td', class_='seasonEpisodeTitle')
                movie_title = title_div.get_text(strip=True).split(' - ')[0] if title_div else "Unknown"
                movie_url = f"{base_url}/filme/film-{index}"

                streaming_services = []
                service_icons = movie.find_all('i', class_='icon')
                for icon in service_icons:
                    service = icon.get('title', 'Unknown')
                    streaming_services.append(service.lower())
                streaming_services = ','.join(streaming_services) if streaming_services else "None"

                languages = set()
                language_flags = movie.find_all('img', class_='flag')
                for flag in language_flags:
                    title = flag.get('title', 'Unknown').lower()
                    if 'deutsch' in title and 'untertitel' not in title:
                        languages.add('ger')
                    elif 'mit deutschem untertitel' in title:
                        languages.add('gersub')
                    elif 'englisch' in title or 'english' in title:
                        languages.add('engsub')
                languages = ','.join(sorted(languages)) if languages else "None"

                movie_info_list.append({
                    'movie_number': index,
                    'movie_name': movie_title,
                    'movie_url': movie_url,
                    'services': streaming_services,
                    'languages': languages
                })

            return movie_info_list
        else:
            if debug:
                print(f"/filme section exists but contains no movies.")
            return []

    except requests.RequestException:
        if debug:
            print(f"/filme section not found or inaccessible.")
        return []

def fetch_total_seasons(base_url, debug=False):
    """Fetch the total number of seasons based on the page meta information."""
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        meta_tag = soup.find('meta', {'itemprop': 'numberOfSeasons'})
        if meta_tag:
            total_seasons = int(meta_tag['content'])
            if debug:
                print(f"Total seasons according to meta: {total_seasons}")
            return total_seasons
        else:
            if debug:
                print("No 'numberOfSeasons' meta tag found.")
            return 0
    except requests.RequestException as e:
        if debug:
            print(f"Error fetching season count: {e}")
        return 0

def fetch_anime_episodes(base_url, debug=False):
    """Fetch anime episodes and movies and organize them into a structured JSON format."""
    try:
        if not base_url.startswith('http'):
            base_url = 'https://aniworld.to' + base_url
        
        if debug:
            print(f"Fetching base URL: {base_url}")

        response = requests.get(base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the anime name
        anime_name = extract_anime_name(soup, debug)

        anime_data = {
            'anime_name': anime_name,
            'total_seasons': 0,
            'total_episodes': 0,
            'movies': {
                'total_movies': 0,
                'movie_list': []
            },
            'seasons': {}
        }

        total_seasons = fetch_total_seasons(base_url, debug)
        if total_seasons == 0:
            print("No seasons information available.")
            return

        movie_info_list = check_filme_section(base_url, debug)
        if movie_info_list:
            anime_data['movies']['total_movies'] = len(movie_info_list)
            anime_data['movies']['movie_list'] = movie_info_list
            total_seasons -= 1

        if total_seasons == 0:
            print("No valid seasons found.")
        else:
            anime_data['total_seasons'] = total_seasons
            total_episode_count = 0
            for season_number in range(1, total_seasons + 1):
                season_url = f"{base_url}/staffel-{season_number}"
                if debug:
                    print(f"Processing Season {season_number} - {season_url}")

                season_response = requests.get(season_url)
                season_soup = BeautifulSoup(season_response.text, 'html.parser')
                season_container = season_soup.find('tbody', id=f'season{season_number}')

                if not season_container:
                    if debug:
                        print(f"Seasons container not found for Season {season_number}.")
                    continue

                episodes = season_container.find_all('tr', {'itemprop': 'episode'})
                season_data = {
                    'total_episodes': len(episodes),
                    'episodes': {}
                }
                total_episode_count += len(episodes)

                for episode in episodes:
                    episode_number = episode.find('meta', {'itemprop': 'episodeNumber'})['content']
                    title_div = episode.find('td', class_='seasonEpisodeTitle')
                    episode_title = title_div.get_text(strip=True).split(' - ')[0] if title_div else "Unknown"
                    episode_url = f"{base_url}/staffel-{season_number}/episode-{episode_number}"

                    streaming_services = []
                    service_icons = episode.find_all('i', class_='icon')
                    for icon in service_icons:
                        service = icon.get('title', 'Unknown')
                        streaming_services.append(service.lower())
                    streaming_services = ','.join(streaming_services) if streaming_services else "None"

                    languages = set()
                    language_flags = episode.find_all('img', class_='flag')
                    for flag in language_flags:
                        title = flag.get('title', 'Unknown').lower()
                        if 'deutsch' in title and 'untertitel' not in title:
                            languages.add('ger')
                        elif 'mit deutschem untertitel' in title:
                            languages.add('gersub')
                        elif 'englisch' in title or 'english' in title:
                            languages.add('engsub')
                    languages = ','.join(sorted(languages)) if languages else "None"

                    season_data['episodes'][f"E{episode_number}"] = {
                        'episode_title': episode_title,
                        'episode_url': episode_url,
                        'services': streaming_services,
                        'languages': languages
                    }

                anime_data['seasons'][f"Season {season_number}"] = season_data

            anime_data['total_episodes'] = total_episode_count

    except requests.RequestException as e:
        print(f"Error fetching anime details: {e}")

    # Save the structured data as a JSON file in the 'data' directory
    file_path = os.path.join(DATA_DIR, "data.json")
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(anime_data, json_file, ensure_ascii=False, indent=4)
        print(f"Anime data saved to {file_path}")

# Example usage
url = '/anime/stream/death-note'
fetch_anime_episodes(url, debug=True)
