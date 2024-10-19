import os
import json
import httpx
import re
import time
from bs4 import BeautifulSoup

BASE_URL = 'https://aniworld.to'

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_m3u8_url(redirect_url, retries=3, delay=3, debug=False):
    """Fetches the m3u8 URL by following the redirect from the VOE link with retry logic."""
    for attempt in range(retries):
        try:
            if debug:
                print(f"Fetching VOE URL: {redirect_url} (Attempt {attempt + 1}/{retries})")

            with httpx.Client(follow_redirects=True, timeout=30) as client:
                response = client.get(redirect_url)
                final_url = str(response.url)

                if debug:
                    print(f"Final redirected URL: {final_url}")

                # Check for a JavaScript-based redirect within the page content
                soup = BeautifulSoup(response.text, 'html.parser')
                script_tag = soup.find('script', string=re.compile(r'window\.location\.href'))
                if script_tag:
                    match = re.search(r'window\.location\.href\s*=\s*[\'"]([^\'"]+)[\'"]', script_tag.string)
                    if match:
                        redirect_js_url = match.group(1)
                        if debug:
                            print(f"Found JavaScript redirect URL: {redirect_js_url}")
                        
                        # Follow the JS redirect manually
                        response = client.get(redirect_js_url)
                        final_url = str(response.url)
                        if debug:
                            print(f"Final redirected URL after JavaScript redirect: {final_url}")

                # Extract the m3u8 URL from the final response content
                m3u8_match = re.search(r'(https://[^"\']+\.m3u8[^\s"\']*)', response.text, re.IGNORECASE)
                if m3u8_match:
                    m3u8_url = m3u8_match.group(1)
                    if debug:
                        print(f"Found m3u8 URL: {m3u8_url}")
                    return m3u8_url
                else:
                    if debug:
                        print(f"Failed to find the m3u8 URL in {final_url}")
                    return None

        except httpx.RequestError as e:
            print(f"Error fetching {redirect_url}, retrying ({attempt + 1}/{retries})...: {e}")
            time.sleep(delay)
    return None

def process_voe_links_from_json(json_file, output_file="m3u8_data.json", retries=3, debug=False):
    """Process VOE links from a JSON file and fetch m3u8 links with retry and delay logic."""
    try:
        json_path = os.path.join(DATA_DIR, json_file)
        output_path = os.path.join(DATA_DIR, output_file)

        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        m3u8_data = {}
        success_count = 0
        failed_count = 0
        total_count = 0

        for episode_name, languages in data.items():
            if not isinstance(languages, dict):
                print(f"Skipping invalid data in episode: {episode_name}")
                continue

            m3u8_data[episode_name] = {}
            for language, services in languages.items():
                if isinstance(services, list):
                    voe_service = next((service for service in services if 'VOE' in service['service_name']), None)
                    if voe_service:
                        total_count += 1
                        m3u8_url = fetch_m3u8_url(voe_service['stream_url'], retries=retries, debug=debug)
                        if m3u8_url:
                            if debug:
                                print(f"m3u8 URL found for {episode_name} ({language}): {m3u8_url}")
                            m3u8_data[episode_name][language] = m3u8_url
                            success_count += 1
                        else:
                            if debug:
                                print(f"Failed to fetch m3u8 URL for {episode_name} ({language})")
                            failed_count += 1
                else:
                    print(f"Skipping non-list services in {episode_name} ({language})")

        # Save m3u8 data to a new JSON file
        with open(output_path, 'w', encoding='utf-8') as outfile:
            json.dump(m3u8_data, outfile, ensure_ascii=False, indent=4)
        print(f"m3u8 data saved to {output_path}")

        # Display success and failure statistics
        print(f"Success: {success_count}/{total_count}")
        print(f"Failed: {failed_count}/{total_count}")

    except FileNotFoundError:
        print(f"File {json_file} not found in {DATA_DIR}.")
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}")

# Example usage
json_file = 'extracted_data.json'  # Replace with your JSON file
process_voe_links_from_json(json_file, output_file="m3u8_data.json", retries=3, debug=True)
