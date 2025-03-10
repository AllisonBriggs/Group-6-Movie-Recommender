import requests
from models import db, Movie
from flask import Flask
from datetime import datetime
import pandas as pd

# Flask App Initialization
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Load the CSV dataset
file_path = "Movie_Database.csv"  # Update with correct path
df = pd.read_csv(file_path, encoding="ISO-8859-1")

# API Keys
TMDB_API_KEY = "be7a1b6d19aadf8e429820ead6d4c592"
IMDB_API_KEY = "8bc777d3"

def get_cast_from_imdb(imdb_id):
    """Fetches top 5 cast members from IMDb API using the IMDb ID."""
    url = f"https://imdb-api.com/en/API/FullCast/{IMDB_API_KEY}/{imdb_id}"
    
    try:
        response = requests.get(url, timeout=10)  # Set a timeout to prevent hanging
        if response.status_code == 429:
            print("Error: Rate limit exceeded! Wait until the next day.")
        response.raise_for_status()  # Raises an error if the response status is not 200
        data = response.json()

        if "cast" in data and isinstance(data["cast"], list):
            cast_list = [actor["name"] for actor in data["cast"][:5]]  # Get top 5 actors
            return ", ".join(cast_list)

        if "items" in data and isinstance(data["items"], list):
            cast_list = [actor["name"] for actor in data["items"][:5]]  # Alternate key
            return ", ".join(cast_list)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching cast for {imdb_id}: {e}")
        return "No cast data available"

    return "No cast data available"


# Function to fetch movie poster from TMDb API
def get_movie_poster(movie_title):
    """Fetches movie poster URL from TMDb API"""
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_title}"
    response = requests.get(url).json()
    
    if response["results"]:
        poster_path = response["results"][0].get("poster_path", None)
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"  # TMDb image base URL
    
    return None  # Return None if no poster found

# TESTING GET_MOVIE_POSTER BY ADDING ONE MOVIE MANUALLY
"""
def add_nosferatu_to_db():
    #Adds Nosferatu (2024) movie to the database with its poster
    title = "Nosferatu"
    
    # Fetch Nosferatu's poster
    poster_url = get_movie_poster(title)
    

    # Check if Nosferatu is already in the database
    new_movie = Movie(
        title=title,
        release_date="2024-12-25",  # Nosferatu’s release date
        director="Robert Eggers",
        genre="Horror",
        cast_members="Bill Skarsgård, Nicholas Hoult, Lily-Rose Depp, Aaron Taylor-Johnson",
        poster_url=poster_url
    )
    db.session.add(new_movie)

    db.session.commit()
    print(f" '{title}' added to the database with poster!")
    """



def get_movie_summary(movie_title):
    """Fetches movie summary (overview) from TMDb API and prints response."""
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_title}"
    
    response = requests.get(url).json()

    print(f"Fetching summary for: {movie_title}")  # Debugging
    print("API Response:", response)  # Debugging: Print full API response
    
    if "results" in response and response["results"]:
        summary = response["results"][0].get("overview", "No summary available.")
        print(f"Summary Found: {summary}")  # Debugging: Check summary
        return summary
    
    print("No summary found!")  # Debugging: If no summary exists
    return "No summary available."


# Insert movies into the database
with app.app_context():
    for index, row in df.iterrows():
        title = row["Movie"]
        year = row["Year"]
        genres = row["Genres"]
        imdb_id = row["IMDb ID"]
        director = row["Director"]
        writer = row["Writer"]
        tv_rating = row["Certification/Rating"]

        # Convert release year to a full date (assuming January 1st)
        release_date = datetime.strptime(f"{year}-01-01", "%Y-%m-%d")

        # Fetch cast members from IMDb
        #cast_members = get_cast_from_imdb(imdb_id)

        # Fetch movie poster from TMDb
        poster_url = get_movie_poster(title)

        # Check if movie already exists to prevent duplicates
        existing_movie = Movie.query.filter_by(title=title).first()
        if existing_movie:
            # Fetch the summary
            summary = get_movie_summary(title)
            
            if not existing_movie.summary or existing_movie.summary == "No summary available.":
                existing_movie.summary = summary  # Update the summary
                db.session.commit()  # Save the update
                print(f"Updated summary for {title}: {summary}")
            else:
                print(f"Skipping {title}, summary already exists.")
            continue


        summary = get_movie_summary(title)

        # Create and add the movie to the database
        new_movie = Movie(
            title=title,
            release_date=release_date,
            director=director,
            writer=writer,
            genre=genres,
            #cast_members=cast_members,
            tv_rating=tv_rating,
            poster_url=poster_url,
            summary=summary
        )
        db.session.add(new_movie)
        print(f"added movie{title}")

    db.session.commit()
    print("Movies successfully added to the database!")
