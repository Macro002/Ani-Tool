import os
import json
import requests
from bs4 import BeautifulSoup
import time
import logging

# Base URL for the website
BASE_URL = 'https://aniworld.to'

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger()

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, 'ani-tool', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def extract_stream_links(content_url, debug=False):
    """Extract streaming services and language options for a movie or episode."""
    try:
        logger.info(f"Processing URL: {content_url}")

        # Ensure the URL starts with BASE_URL only if it's not already a full URL
        if not content_url.startswith(BASE_URL):
            content_url = f"{BASE_URL}{content_url}"

        # Retry mechanism in case of network issues with exponential backoff
        max_retries = 3
        delay = 2
        for attempt in range(max_retries):
            try:
                response = requests.get(content_url, timeout=15)
                response.raise_for_status()
                break  # If successful, exit the loop
            except requests.RequestException as e:
                logger.warning(f"Error fetching {content_url}, retrying ({attempt + 1}/{max_retries}) in {delay} seconds...: {e}")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
        else:
            logger.error(f"Failed to fetch {content_url} after {max_retries} retries.")
            return {}

        # Process the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find available languages by locating the images in the `changeLanguageBox` section
        languages = {}
        language_box = soup.find('div', class_='changeLanguageBox')
        if language_box:
            lang_images = language_box.find_all('img')
            for lang in lang_images:
                lang_title = lang.get('title', '').lower().replace(' ', '-')
                lang_key = lang.get('data-lang-key')
                if lang_title and lang_key:
                    languages[lang_key] = lang_title

        if debug:
            logger.info(f"Languages found: {languages}")

        # Find available streaming services for each language
        services = {}
        episode_links = soup.find_all('li', class_=['col-md-3', 'col-xs-12', 'col-sm-6'])
        for link in episode_links:
            lang_key = link.get('data-lang-key')
            link_url = link.get('data-link-target')  # The redirect link
            service_name = link.find('h4').get_text(strip=True) if link.find('h4') else 'Unknown'

            if lang_key in languages and link_url:
                if lang_key not in services:
                    services[lang_key] = []
                services[lang_key].append({
                    'service_name': service_name,
                    'stream_url': BASE_URL + link_url  # Full URL for the stream
                })

        if debug:
            logger.info(f"Services found: {services}")

        # Combine language options and their respective streaming services
        content_data = {}
        for lang_key, lang_name in languages.items():
            content_data[lang_name] = services.get(lang_key, [])

        return content_data

    except requests.RequestException as e:
        logger.error(f"Failed to extract data from {content_url}: {e}")
        return {}

def process_content_from_json(json_file, debug=False):
    """Process movies and episodes from the JSON file and extract streaming links."""
    try:
        # Open and load the JSON file from the data directory
        json_path = os.path.join(DATA_DIR, json_file)
        with open(json_path, 'r', encoding='utf-8') as file:
            anime_data = json.load(file)

        content_links_data = {}
        processed_count = 0  # Track the number of processed movies/episodes

        # Process Movies
        movie_list = anime_data.get('movies', {}).get('movie_list', [])
        if movie_list:
            logger.info(f"Processing {len(movie_list)} movies...")
            for movie in movie_list:
                movie_number = movie['movie_number']
                movie_title = f"S0E{movie_number} - {movie['movie_name']}"  # Formatting as S0E1 for movies
                movie_url = movie['movie_url']
                logger.info(f"Fetching data for movie: {movie_title}...")

                # Extract stream links for this movie
                movie_links = extract_stream_links(movie_url, debug)
                content_links_data[movie_title] = movie_links

                processed_count += 1

        # Process Seasons and Episodes
        seasons = anime_data.get('seasons', {})
        for season_name, season_data in seasons.items():
            episodes = season_data.get('episodes', {})
            logger.info(f"Processing {len(episodes)} episodes in {season_name}...")
            season_number = season_name.split(' ')[1]  # Extracting season number
            for episode_id, episode_data in episodes.items():
                episode_title = f"S{season_number}E{episode_id[1:]} - {episode_data['episode_title']}"  # Formatting as S1E1
                episode_url = episode_data['episode_url']
                logger.info(f"Fetching data for episode: {episode_title}...")

                # Extract stream links for this episode
                episode_links = extract_stream_links(episode_url, debug)
                content_links_data[episode_title] = episode_links

                processed_count += 1

        # Save the extracted movie and episode links to a new JSON file in the data directory
        output_file = os.path.join(DATA_DIR, f"extracted_{json_file}")
        with open(output_file, 'w', encoding='utf-8') as outfile:
            json.dump(content_links_data, outfile, ensure_ascii=False, indent=4)
        logger.info(f"Extracted data saved to {output_file}")

    except FileNotFoundError:
        logger.error(f"File {json_file} not found in {DATA_DIR}.")
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON in {json_file}.")

# Example usage
json_file = 'data.json'  # The JSON file must be located in the 'data' directory
process_content_from_json(json_file, debug=True)
