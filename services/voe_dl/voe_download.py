import os
import json
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')

def convert_m3u8_to_mp4(m3u8_url, output_file):
    """Uses ffmpeg to download an m3u8 URL and save it as an MP4 file."""
    try:
        command = [
            'ffmpeg',
            '-i', m3u8_url,   # Input m3u8 URL
            '-c', 'copy',      # Copy codec (no re-encoding)
            '-bsf:a', 'aac_adtstoasc',  # Required for proper audio stream handling
            output_file        # Output file
        ]
        
        # Run the ffmpeg command
        subprocess.run(command, check=True)
        print(f"Conversion completed: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg failed with error: {e}")

def download_anime_content(m3u8_json_file, anime_data_file, retries=3, debug=False):
    """Download anime movies and episodes in the correct structure."""
    # Load m3u8 links from the json file
    m3u8_json_path = os.path.join(DATA_DIR, m3u8_json_file)
    anime_data_path = os.path.join(DATA_DIR, anime_data_file)

    try:
        # Load m3u8 data
        with open(m3u8_json_path, 'r', encoding='utf-8') as m3u8_file:
            m3u8_data = json.load(m3u8_file)

        # Load anime name and episode titles from data.json
        with open(anime_data_path, 'r', encoding='utf-8') as anime_data_file:
            anime_data = json.load(anime_data_file)

        anime_name = anime_data['anime_name']

        # Create main download folder for the anime
        anime_dir = os.path.join(DOWNLOADS_DIR, anime_name)
        os.makedirs(anime_dir, exist_ok=True)

        # Language folder names mapping
        language_folders = {
            'deutsch': 'german',
            'mit-untertitel-deutsch': 'german_sub',
            'english_sub': 'english_sub'  # If there's any entry for english_sub
        }

        # Prepare language directories with seasons and movies subdirectories
        for lang in language_folders.values():
            lang_dir = os.path.join(anime_dir, lang)
            os.makedirs(os.path.join(lang_dir, 'seasons'), exist_ok=True)
            os.makedirs(os.path.join(lang_dir, 'movies'), exist_ok=True)

        # Track episode download status
        total_episodes = 0
        downloaded_episodes = 0

        # Process m3u8 links and download content
        for episode_name, languages in m3u8_data.items():
            if debug:
                print(f"Processing episode: {episode_name}")

            for language, m3u8_url in languages.items():
                if language in language_folders:
                    total_episodes += 1

                    # Get the episode title from data.json or movies section
                    episode_title = ""
                    if "S0E" in episode_name:
                        # Movies go into the movies folder
                        movie_number = int(episode_name.split('-')[0][3:])  # Extract movie number from S0E1 format
                        movie_data = next((movie for movie in anime_data['movies']['movie_list'] if movie['movie_number'] == movie_number), None)
                        if movie_data:
                            episode_title = movie_data['movie_name']
                        output_subdir = 'movies'
                    else:
                        # Episodes go into the seasons folder directly (no subfolder per episode)
                        season_num = episode_name.split(' ')[0][1:]  # Extract season number
                        episode_data = anime_data.get('seasons', {}).get(f'Season {season_num}', {}).get('episodes', {}).get(episode_name, {})
                        episode_title = episode_data.get('episode_title', episode_name)
                        output_subdir = 'seasons'  # All episodes go here

                    # Ensure the episode title is formatted correctly for filenames
                    episode_title = episode_title.replace(' ', '_') if episode_title.strip() else 'unknown_episode'

                    # Prevent double appending of episode titles
                    episode_filename = f"{episode_name}_{episode_title}.mp4" if episode_title != episode_name.split(' - ')[1].strip() else f"{episode_name}.mp4"

                    # Path to save the episode in the correct language folder (directly in seasons/movies, no additional episode subfolder)
                    output_path = os.path.join(anime_dir, language_folders[language], output_subdir, episode_filename)
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)  # Ensure the subdirectory exists

                    if debug:
                        print(f"Downloading {episode_name} ({language}) to {output_path}")
                        print(f"m3u8 URL: {m3u8_url}")

                    # Check if the m3u8 URL is valid
                    if not m3u8_url:
                        print(f"No m3u8 URL found for {episode_name} ({language})")
                        continue

                    # Download the episode
                    convert_m3u8_to_mp4(m3u8_url, output_path)
                    downloaded_episodes += 1

        # Cleanup: remove empty language folders
        for lang, folder in language_folders.items():
            lang_dir = os.path.join(anime_dir, folder)
            for subfolder in ['movies', 'seasons']:
                subfolder_path = os.path.join(lang_dir, subfolder)
                if not any(os.scandir(subfolder_path)):  # Check if folder is empty
                    print(f"Removing empty folder: {subfolder_path}")
                    shutil.rmtree(subfolder_path)

        print(f"Download completed. Total episodes: {total_episodes}, Downloaded: {downloaded_episodes}")

    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")

# Example usage
m3u8_json_file = 'm3u8_data.json'
anime_data_file = 'data.json'
download_anime_content(m3u8_json_file, anime_data_file, retries=3, debug=True)
