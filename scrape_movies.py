import pandas as pd
import requests
from bs4 import BeautifulSoup

# Wikipedia page for 2024 films
URL = "https://en.wikipedia.org/wiki/List_of_American_films_of_2024"

def scrape_wikipedia_movies(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all tables containing movie data (Wikipedia lists movies in multiple tables)
    tables = soup.find_all("table", {"class": "wikitable"})

    movies_list = []

    for table in tables:
        rows = table.find_all("tr")[1:]  # Skip the header row

        for row in rows:
            cols = row.find_all(["th", "td"])  # Some tables use <th> for titles
            if len(cols) < 5:  # Ensure valid row
                continue

            # Extract data from columns
            title = cols[0].get_text(strip=True) if len(cols) > 0 else "N/A"
            director = cols[1].get_text(strip=True) if len(cols) > 1 else "N/A"
            cast = cols[2].get_text(strip=True) if len(cols) > 2 else "N/A"
            genre = cols[3].get_text(strip=True) if len(cols) > 3 else "N/A"
            release_date = cols[4].get_text(strip=True) if len(cols) > 4 else "N/A"

            movies_list.append({
                "Title": title,
                "Director": director,
                "Cast": cast,
                "Genre": genre,
                "Release Date": release_date
            })

    return movies_list

# Scrape movies
movies = scrape_wikipedia_movies(URL)

# Save to CSV
df = pd.DataFrame(movies)
df.to_csv("movies_2024.csv", index=False)

print("Movie data saved as 'movies_2024.csv'")
