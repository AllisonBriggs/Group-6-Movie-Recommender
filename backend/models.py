from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from scipy.spatial.distance import cosine
import numpy as np
from datetime import datetime
import pandas as pd

VALID_GENRES = {
    'Action', 'Adult', 'Adventure', 'Animation', 'Biography', 'Comedy', 
    'Crime', 'Documentary', 'Drama', 'Family', 'Fantasy', 'History', 'Horror', 
    'Music', 'Mystery', 'News', 'Romance', 'Sci-Fi', 'Short', 'Sport', 'Thriller', 
    'War', 'Western'
}

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    favorite_genres = db.Column(db.String(800), nullable=True)

    def __init__(self, username, password, favorite_genres=""):
        self.username = username
        self.set_password(password)
        self.favorite_genres = favorite_genres

    def set_password(self, password):
        """Hashes password before storing"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Verifies password"""
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"
    
    def set_favorite_genres(self, genres):
        """Store genres as a comma-separated string"""
        self.favorite_genres = ", ".join(genres)
        db.session.commit()

    def get_favorite_genres(self):
        return self.favorite_genres.split(",") if self.favorite_genres else []
    
    def set_favorite_movies(self, movies):
        """Store movies as a comma-separated string"""
        self.favorite_movies = ", ".join(map(str, movies))
        db.session.commit()

    def get_favorite_movies(self):
        """Return movies as a list"""
        return self.favorite_movies.split(", ") if self.favorite_movies else []
        

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    release_date = db.Column(db.String(100), nullable=True)
    average_rating = db.Column(db.Float, default=0.0)
    director = db.Column(db.String(100), nullable=True)
    writer = db.Column(db.String(100), nullable=True)
    genre = db.Column(db.Text, nullable=True)
    cast_members = db.Column(db.Text, nullable=True)  # Store as a comma-separated string
    tv_rating = db.Column(db.String(100), nullable=True)
    poster_url = db.Column(db.String(300), nullable=True)
    summary = db.Column(db.String(800), nullable=True)

    def __init__(self, title, release_date, director, genre, writer, tv_rating, summary, poster_url=None, ):
        self.title = title
        self.release_date = release_date
        self.director = director
        self.genre = genre
        #self.cast_members = cast_members
        self.poster_url = poster_url
        writer = writer
        tv_rating = tv_rating
        summary = summary

    def __repr__(self):
        return f"<Movie {self.title}>"

    def update_rating(self, new_rating):
        self.average_rating = new_rating
        db.session.commit()

    def add_cast_member(self, member_name):
        if self.cast_members:
            self.cast_members += f", {member_name}"
        else:
            self.cast_members = member_name
        db.session.commit()

    def remove_cast_member(self, member_name):
        if self.cast_members:
            cast_list = self.cast_members.split(", ")
            if member_name in cast_list:
                cast_list.remove(member_name)
                self.cast_members = ", ".join(cast_list)
        db.session.commit()

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey("movie.id"), nullable=False)
    rating = db.Column(db.Float, nullable=False)

class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey("movie.id"), nullable=False)

class Recommendation:
    def __init__(self, user, movie_db):
        self.user = user
        self.movie_db = movie_db

    def __repr__(self):
        return f"<Recommendation for {self.user.username}>"

    def rec_by_genre(self):
        user_genres = self.user.favorited_genres.split(", ")
        return [movie for movie in self.movie_db if any(genre in movie.genre for genre in user_genres)]

    def rec_by_favorites(self):
        return self.user.favorited_movies

    def rec_top_rated(self):
        return sorted(self.movie_db, key=lambda x: x.average_rating, reverse=True)[:10]

    def rec_trending(self):
        # Placeholder: Ideally, fetch trending movies based on recent activity
        return self.movie_db[:10]
    

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    review_text = db.Column(db.Text, nullable=True)
    review_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", backref="reviews")  # <- THIS is key

    def __init__(self, user_id, movie_id, rating, review_text):
        self.user_id = user_id
        self.movie_id = movie_id
        self.rating = rating
        self.review_text = review_text

    def __repr__(self):
        return f"<Review {self.id} by User {self.user_id}>"

    def update_review(self, new_rating, new_text):
        self.rating = new_rating
        self.review_text = new_text
        db.session.commit()

    def delete_review(self):
        db.session.delete(self)
        db.session.commit() 