import os
import json
import requests
from bs4 import BeautifulSoup
import time

BASE_URL = 'https://aniworld.to'

def follow_redirect_and_get_final_url(redirect_url, debug=False):
    """Follow the redirect URL and return the final destination URL."""
    try:
        if debug:
            print(f"Visiting redirect URL: {redirect_url}")
        
        response = requests.get(redirect_url, timeout=10, allow_redirects=True)
        # Get the final URL after the redirect
        final_url = response.url
        if debug:
            print(f"Final redirected URL: {final_url}")
        return final_url
    except requests.RequestException as e:
        print(f"Failed to follow redirect for {redirect_url}: {e}")
        return None

def extract_movie_stream_links(movie_url, debug=False):
    """Extract streaming services and language options for a movie."""
    try:
        if debug:
            print(f"Processing movie URL: {movie_url}")

        # Ensure the URL starts with BASE_URL only if it's not already a full URL
        if not movie_url.startswith(BASE_URL):
            movie_url = f"{BASE_URL}{movie_url}"

        # Retry mechanism in case of network issues
        max_retries = 3
        for _ in range(max_retries):
            try:
                response = requests.get(movie_url, timeout=10)
                response.raise_for_status()
                break
            except requests.RequestException as e:
                if debug:
                    print(f"Error fetching {movie_url}, retrying...: {e}")
                time.sleep(2)
        else:
            print(f"Failed to fetch {movie_url} after {max_retries} retries.")
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
            print(f"Languages found: {languages}")

        # Find available streaming services for each language
        services = {}
        episode_links = soup.find_all('li', class_=['col-md-3', 'col-xs-12', 'col-sm-6'])
        for link in episode_links:
            lang_key = link.get('data-lang-key')
            link_target = link.get('data-link-target')  # Check if 'data-link-target' exists
            if link_target:
                redirect_url = BASE_URL + link_target  # Full URL for the redirect
                service_name = link.find('h4').get_text(strip=True) if link.find('h4') else 'Unknown'

                # Follow the redirect to get the final streaming URL
                final_url = follow_redirect_and_get_final_url(redirect_url, debug)
                
                if lang_key in languages and final_url:
                    if lang_key not in services:
                        services[lang_key] = []
                    services[lang_key].append({
                        'service_name': service_name,
                        'stream_url': final_url  # Save the final URL after the redirect
                    })

        if debug:
            print(f"Services found: {services}")

        # Combine language options and their respective streaming services
        movie_data = {}
        for lang_key, lang_name in languages.items():
            movie_data[lang_name] = services.get(lang_key, [])

        return movie_data

    except requests.RequestException as e:
        print(f"Failed to extract data from {movie_url}: {e}")
        return {}

def process_movies_from_json(json_file, debug=False):
    """Process movies from the JSON file and extract streaming links."""
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            anime_data = json.load(file)
        
        movie_list = anime_data.get('movies', {}).get('movie_list', [])
        if not movie_list:
            print(f"No movies found in {json_file}")
            return

        movie_links_data = {}
        for movie in movie_list:
            movie_title = movie['movie_name']
            movie_url = movie['movie_url']  # Ensure proper URL formatting
            if debug:
                print(f"Fetching data for {movie_title}...")

            # Extract stream links for this movie
            movie_links = extract_movie_stream_links(movie_url, debug)
            movie_links_data[movie_title] = movie_links

        # Save the extracted movie links to a new JSON file
        output_file = f"extracted_{os.path.basename(json_file)}"
        with open(output_file, 'w', encoding='utf-8') as outfile:
            json.dump(movie_links_data, outfile, ensure_ascii=False, indent=4)
        print(f"Extracted movie data saved to {output_file}")

    except FileNotFoundError:
        print(f"File {json_file} not found.")

# Example usage
json_file = 'one-piece.json'  # Replace with the correct JSON file in your directory
process_movies_from_json(json_file, debug=True)
