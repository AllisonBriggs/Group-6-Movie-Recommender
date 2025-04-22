from models import User, Movie, Rating
from sqlalchemy.sql.expression import func
from sqlalchemy import desc
from collections import defaultdict
import numpy as np
from scipy.spatial.distance import cosine

class Recommendation:
    def __init__(self, user, db_session):
        self.user = user
        self.db_session = db_session
        self.movie_db = Movie.query.all()

    def __repr__(self):
        return f"<Recommendation for {self.user.username}>"

    def rec_by_genre(self, limit=5):
        """Return movies based on user's favorite genres."""
        genre_matches = []
        user_genres = self.user.get_favorite_genres()
        if not user_genres:
            return []

        for genre in user_genres:
            matches = Movie.query.filter(
                Movie.genre.ilike(f"%{genre}%")
            ).order_by(func.random()).limit(limit).all()
            genre_matches.extend(matches)

        return genre_matches

    def rec_by_favorites(self, top_n=10):
        """Recommend similar movies based on user's favorite movies."""
        fav_ids = self.user.get_favorite_movies()
        if not fav_ids:
            return []

        favorites = Movie.query.filter(Movie.id.in_(fav_ids)).all()
        favorite_genres = set()
        for movie in favorites:
            if movie.genre:
                favorite_genres.update(g.strip() for g in movie.genre.split(",") if g.strip())

        candidates = Movie.query.filter(
            ~Movie.id.in_(fav_ids)
        ).all()

        similar_movies = []
        for movie in candidates:
            if movie.genre:
                movie_genres = set(g.strip() for g in movie.genre.split(","))
                if favorite_genres & movie_genres:
                    similar_movies.append(movie)

        return sorted(similar_movies, key=lambda m: m.average_rating, reverse=True)[:top_n]

    def rec_top_rated(self, top_n=10):
        """Return highest-rated movies overall."""
        return Movie.query.order_by(desc(Movie.average_rating)).limit(top_n).all()


    def rec_trending(self, limit=10):
        """Returns trending movies (random selection for now)."""
        return Movie.query.order_by(func.random()).limit(limit).all()

    def rec_by_similarity(self, top_n=10):
        """Collaborative filtering using cosine similarity."""
        all_ratings = Rating.query.all()
        user_ratings = {r.movie_id: r.rating for r in Rating.query.filter_by(user_id=self.user.id).all()}
        if not user_ratings:
            return []

        # Build user -> movie rating vectors
        user_profiles = defaultdict(dict)
        for r in all_ratings:
            user_profiles[r.user_id][r.movie_id] = r.rating

        similarities = []
        for uid, ratings in user_profiles.items():
            if uid == self.user.id:
                continue
            common_movies = set(user_ratings.keys()) & set(ratings.keys())
            if len(common_movies) < 3:
                continue
            u_vec = np.array([user_ratings[mid] for mid in common_movies])
            o_vec = np.array([ratings[mid] for mid in common_movies])
            similarity = 1 - cosine(u_vec, o_vec)
            similarities.append((uid, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)
        recommended = set()
        seen = set(user_ratings.keys())

        for uid, _ in similarities[:5]:
            for mid, rating in user_profiles[uid].items():
                if mid not in seen and rating >= 4.0:
                    recommended.add(mid)
                if len(recommended) >= top_n:
                    break
            if len(recommended) >= top_n:
                break

        return Movie.query.filter(Movie.id.in_(recommended)).all()
