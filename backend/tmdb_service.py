import requests
from models import db, Movie

TMDB_API_KEY = "be7a1b6d19aadf8e429820ead6d4c592"

def get_movie_poster(movie_title):
    """Fetches movie poster URL from TMDb API"""
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_title}"
    response = requests.get(url).json()
    
    if response["results"]:
        poster_path = response["results"][0].get("poster_path", None)
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500{poster_path}"  # TMDb image base URL
    
    return None  # Return None if no poster found

def add_nosferatu_to_db():
    """Adds Nosferatu (2024) movie to the database with its poster"""
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


def get_movie_summary(movie_title):
    """Fetches movie summary (overview) from TMDb API."""
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_title}"
    response = requests.get(url).json()
    
    if response["results"]:
        return response["results"][0].get("overview", "No summary available.")
    
    return "No summary found."

# Example usage:
movie_title = "Nosferatu"
summary = get_movie_summary(movie_title)
print(f"Summary of {movie_title}: {summary}")
