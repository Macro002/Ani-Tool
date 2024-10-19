import os
import requests
import subprocess
import shutil
from bs4 import BeautifulSoup

# Constants
base_url = 'https://aniworld.to'
anime_list = []
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Adjusted for two levels up
DATA_DIR = os.path.join(BASE_DIR, 'data')
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')

# Logo
logo = """
 ▄▄▄       ███▄    █  ██▓   ▄▄▄█████▓ ▒█████   ▒█████   ██▓    
▒████▄     ██ ▀█   █ ▓██▒   ▓  ██▒ ▓▒▒██▒  ██▒▒██▒  ██▒▓██▒    
▒██  ▀█▄  ▓██  ▀█ ██▒▒██▒   ▒ ▓██░ ▒░▒██░  ██▒▒██░  ██▒▒██░    
░██▄▄▄▄██ ▓██▒  ▐▌██▒░██░   ░ ▓██▓ ░ ▒██   ██░▒██   ██░▒██░    
 ▓█   ▓██▒▒██░   ▓██░░██░     ▒██▒ ░ ░ ████▓▒░░ ████▓▒░░██████▒
 ▒▒   ▓▒█░░ ▒░   ▒ ▒ ░▓       ▒ ░░   ░ ▒░▒░▒░ ░ ▒░▒░▒░ ░ ▒░▓  ░
  ▒   ▒▒ ░░ ░░   ░ ▒░ ▒ ░       ░      ░ ▒ ▒░   ░ ▒ ▒░ ░ ░ ▒  ░
  ░   ▒      ░   ░ ░  ▒ ░     ░      ░ ░ ░ ▒  ░ ░ ░ ▒    ░ ░   
      ░  ░         ░  ░                  ░ ░      ░ ░      ░  ░
                                                               
"""

def clear_screen():
    """Clears the terminal screen."""
    if os.name == 'nt':
        os.system('cls')  # For Windows
    else:
        os.system('clear')  # For Linux/Unix/Mac

def clean_data_directory():
    """Clean the /data directory by deleting all files inside it."""
    for filename in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    print(f"Cleaned data directory: {DATA_DIR}")

def run_script_in_background(script_path, *args):
    """Run a Python script in the background using subprocess and wait for it to complete."""
    subprocess.run(["python", script_path] + list(args), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def download_anime(anime):
    """Handle the download process for the selected anime."""
    print("Cleaning previous data...")
    clean_data_directory()  # Step 1: Clean the data directory
    print("Gathering anime info...")

    # Step 2: Execute info_getter.py
    info_getter_script = os.path.join(os.path.dirname(__file__), "info_getter.py")
    run_script_in_background(info_getter_script)
    print("Gathering anime info... done.")

    print("Extracting anime info...")
    # Step 3: Execute extractor.py
    extractor_script = os.path.join(os.path.dirname(__file__), "extractor.py")
    run_script_in_background(extractor_script)
    print("Extracting anime info... done.")

    print("Gathering m3u8 URLs...")
    # Step 4: Execute voe_extract.py
    voe_extract_script = os.path.join(BASE_DIR, "services", "voe_dl", "voe_extract.py")
    run_script_in_background(voe_extract_script)
    print("Gathering m3u8 URLs... done.")

    print("Downloading anime content...")
    # Step 5: Execute voe_download.py
    voe_download_script = os.path.join(BASE_DIR, "services", "voe_dl", "voe_download.py")
    run_script_in_background(voe_download_script)
    print(f"Download process for {anime['name']} has been completed.")

def fetch_anime_list():
    """Scrape the anime list from the website and populate anime_list."""
    url = f'{base_url}/animes'
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        series_container = soup.find('div', id='seriesContainer')
        if series_container:
            genres = series_container.find_all('div', class_='genre')
            for genre in genres:
                genre_name = genre.find('h3').text.strip()
                anime_items = genre.find_all('li')

                for anime_item in anime_items:
                    anime_name = anime_item.text.strip()
                    anime_url = anime_item.find('a')['href']
                    full_anime_url = f"{base_url}{anime_url}"
                    anime_list.append({
                        'name': anime_name,
                        'genre': genre_name,
                        'url': full_anime_url
                    })
            print(f"Fetched {len(anime_list)} animes.")
        else:
            print("Could not find the anime list on the webpage.")
    except requests.RequestException as e:
        print(f"Error fetching anime list: {e}")

def search_anime_by_name(search_term):
    """Searches for animes by a partial match on the name."""
    search_term = search_term.lower()
    results = [anime for anime in anime_list if search_term in anime['name'].lower()]

    if not results:
        print("No matches found.")
    else:
        for idx, anime in enumerate(results, 1):
            print(f"[{idx}] {anime['name']} - Genre: {anime['genre']}")
    return results

def search_anime():
    """Search for an anime using a search term."""
    search_term = input("Enter anime name to search (or part of it): ")
    results = search_anime_by_name(search_term)

    if results:
        selected_anime = input("Enter the number of the anime to select (0 to cancel): ")
        if selected_anime.isdigit():
            selected_anime = int(selected_anime)
            if selected_anime == 0:
                clear_screen()  # Clear the screen after canceling the search
                return None
            if 1 <= selected_anime <= len(results):
                return results[selected_anime - 1]
            else:
                print("Invalid selection.")
    clear_screen()  # Clear the screen if no results or invalid input
    return None

def anime_menu(anime):
    """Show the anime menu with various options."""
    while True:
        clear_screen()  # Clear the screen before showing the anime menu
        print(f"\nSelected Anime: {anime['name']}")
        print("Options:")
        print("[1] Search")
        print("[2] Info (Coming Soon...)")
        print("[3] Options (Coming Soon...)")
        print("[4] Download")
        print("[0] Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            return  # Go back to search
        elif choice == "2":
            print("Coming Soon...")
            back_or_exit()
        elif choice == "3":
            print("Coming Soon...")
            back_or_exit()
        elif choice == "4":
            download_anime(anime)  # Start the download process
        elif choice == "0":
            print("Exiting...")
            exit()
        else:
            print("Invalid option, please try again.")

def back_or_exit():
    """Provide option to go back or exit."""
    while True:
        choice = input("Back [1] or Exit [0]: ")
        if choice == "1":
            clear_screen()  # Clear the screen when going back
            break
        elif choice == "0":
            exit()

def main_menu():
    """Main menu loop."""
    while True:
        clear_screen()  # Clear the screen before showing the main menu
        print(logo)
        print("Options:")
        print("[1] Search")
        print("[0] Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            if not anime_list:
                fetch_anime_list()  # Fetch anime list only if not already loaded
            anime = search_anime()
            if anime:
                anime_menu(anime)
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("Invalid option, please try again.")

# Start the main menu
if __name__ == "__main__":
    main_menu()
