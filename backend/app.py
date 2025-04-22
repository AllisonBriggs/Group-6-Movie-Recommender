from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from sqlalchemy.sql.expression import func 
import os
import json
from recommender import Recommendation

# Import models AFTER db initialization
from models import db, User, Movie, Review, Watchlist, Friend

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = "supersecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

#db = SQLAlchemy(app)
db.init_app(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)

# Load logged-in user before each request
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = User.query.get(user_id) if user_id else None

# Initialize Database Tables
@app.cli.command("initdb")
def initdb_command():
    """Creates the database tables."""
    db.create_all()
    print("Database Initialized Successfully!")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Please fill out all fields", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Username already taken, choose another!", "danger")
            return redirect(url_for("register"))

        # Create new user with required parameters
        new_user = User(username=username, password=password)  # Make sure to pass the password!
        
        db.session.add(new_user)
        db.session.commit()

        # Log the user in automatically
        session["user_id"] = new_user.id
        
        flash("Account created! Now please select your favorite genres.", "success")
        return redirect(url_for("select_genres"))

    return render_template("register.html")

# User Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            flash("Logged in successfully!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password", "danger")

    return render_template("login.html")

@app.route("/select_genres", methods=["GET", "POST"])
def select_genres():
    genres = ["Action", "Adult", "Adventure", "Animation", "Biography", "Comedy", "Crime",
        "Documentary", "Drama", "Family", "Fantasy", "Film Noir", "Game Show", "History",
        "Horror", "Musical", "Music", "Mystery", "News", "Reality-TV", "Romance", "Sci-Fi",
        "Short", "Sport", "Talk-Show", "Thriller", "War", "Western"]
    
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    
    if request.method == "POST":
        genre1 = request.form.get('genre1')
        genre2 = request.form.get('genre2')
        genre3 = request.form.get('genre3')

        # Remove empty values and duplicates
        selected_genres = [g for g in [genre1, genre2, genre3] if g]
        if len(set(selected_genres)) != len(selected_genres):
            flash("Please select different genres.", "danger")
            return redirect(url_for('select_genres'))

        favorite_genres = ",".join(selected_genres)
        
        # Update user with selected genres
        user.favorite_genres = favorite_genres
        db.session.commit()

        flash("Genres saved successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("select_genres.html", genres=genres)

# Dashboard (Accessible After Login)
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    selected_genres = user.get_favorite_genres()
    favorite_movie_ids = user.get_favorite_movies()

    recommender = Recommendation(user, db)

    algo_recs = []
    top_rated = []
    genre_recs = {}

    if selected_genres:
        # Only show algo and top-rated *after* user picks favorite movies
        # Check if user has any ratings
        has_reviews = False
        if (Review.query.filter_by(user_id=user.id).count() > 0):
            has_reviews = True

        if favorite_movie_ids:
            if has_reviews:
                algo_recs = recommender.rec_by_similarity()
            else:
                algo_recs = recommender.rec_by_genre()
                # algo_recs = recommender.rec_by_favorites()

            if len(algo_recs) < 10:
                more = recommender.rec_top_rated()
                seen_ids = {m.id for m in algo_recs}
                algo_recs += [m for m in more if m.id not in seen_ids]

            # Deduplicate
            seen = set()
            unique_algo_recs = []
            for m in algo_recs:
                if m.id not in seen:
                    unique_algo_recs.append(m)
                    seen.add(m.id)
            algo_recs = unique_algo_recs

            top_rated = recommender.rec_top_rated()


        # Genre-based recommendations always show if genres are selected
        genre_recs = {genre: [] for genre in selected_genres}
        for movie in recommender.rec_by_genre():
            if not movie.genre:
                continue
            movie_genres = [g.strip() for g in movie.genre.split(",")]
            for user_genre in selected_genres:
                if user_genre in movie_genres:
                    genre_recs[user_genre].append(movie)
                    break  

    return render_template("dashboard.html",
                           username=user.username,
                           algo_movies=algo_recs,
                           genre_movies=genre_recs,
                           top_movies=top_rated,
                           favorite_ids=favorite_movie_ids)


# Acount Route
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        genre1 = request.form.get("genre1")
        genre2 = request.form.get("genre2")
        genre3 = request.form.get("genre3")

        selected_genres = [g for g in [genre1, genre2, genre3] if g]
        if len(set(selected_genres)) != len(selected_genres):
            flash("Please select different genres.", "danger")
            return redirect(url_for("profile"))

        user.favorite_genres = ",".join(selected_genres)
        db.session.commit()
        flash("Favorite genres updated!", "success")
        return redirect(url_for("profile"))

    watchlist_entries = Watchlist.query.filter_by(user_id=user.id).all()
    reviews = Review.query.filter_by(user_id=user.id).all()

    watchlist_movies = [Movie.query.get(entry.movie_id) for entry in watchlist_entries]

    rated_movies = []
    for review in reviews:
        movie = Movie.query.get(review.movie_id)
        if movie:
            rated_movies.append({
                "title": movie.title,
                "rating": review.rating,
                "comment": review.review_text,
                "date": review.review_date.strftime("%Y-%m-%d")
            })

    favorite_movie_ids = user.get_favorite_movies()
    favorite_movies = Movie.query.filter(Movie.id.in_(favorite_movie_ids)).all() if favorite_movie_ids else []

    return render_template(
        "profile.html",
        username=user.username,
        watchlist_movies=watchlist_movies,
        rated_movies=rated_movies,
        selected_genres=user.get_favorite_genres(),
        favorite_movies=favorite_movies  
    )

@app.route("/friends", methods=["GET", "POST"])
def friends():
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    query = request.args.get("query", "")

    # Friend/follower logic (same as before)
    friend_ids = [fid for (fid,) in db.session.query(Friend.friend_id).filter_by(user_id=user.id).all()]
    friends = User.query.filter(User.id.in_(friend_ids)).all()

    follower_ids = [fid for (fid,) in db.session.query(Friend.user_id).filter_by(friend_id=user.id).all()]
    followers = User.query.filter(User.id.in_(follower_ids)).all()

    # Get recent reviews by friends
    recent_friend_reviews = (
        db.session.query(Review, Movie, User)
        .join(Movie, Review.movie_id == Movie.id)
        .join(User, Review.user_id == User.id)
        .filter(Review.user_id.in_(friend_ids))
        .order_by(Review.review_date.desc())
        .limit(20)
        .all()
    )

    # Format for the template
    recent_friend_movies = []
    for review, movie, reviewer in recent_friend_reviews:
        recent_friend_movies.append({
            "title": movie.title,
            "poster_url": movie.poster_url,
            "username": reviewer.username,
            "watched_on": review.review_date,
            "review_text": review.review_text,
            "movie_id": movie.id 
        })


    return render_template(
        "friends.html",
        username=user.username,
        users=[],
        query=query,
        friends=friends,
        followers=followers,
        recent_friend_movies=recent_friend_movies  
    )

@app.route("/friend/<int:user_id>")
def friend_profile(user_id):
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    query = request.args.get("query", "")

    friend = User.query.get_or_404(user_id)
    friend_ids = [fid for (fid,) in db.session.query(Friend.friend_id).filter_by(user_id=user.id).all()]
    my_friends = User.query.filter(User.id.in_(friend_ids)).all()

    profile_friend_ids = [fid for (fid,) in db.session.query(Friend.friend_id).filter_by(user_id=friend.id).filter(Friend.friend_id != user.id).all()]
    profile_friends = User.query.filter(User.id.in_(profile_friend_ids)).all()

    # Get recent reviews by friends
    recent_friend_reviews = (
        db.session.query(Review, Movie, User)
        .join(Movie, Review.movie_id == Movie.id)
        .join(User, Review.user_id == User.id)
        .filter(Review.user_id == friend.id)
        .order_by(Review.review_date.desc())
        .limit(20)
        .all()
    )


    # Format for the template
    recent_friend_movies = []
    for review, movie, reviewer in recent_friend_reviews:
        recent_friend_movies.append({
            "title": movie.title,
            "poster_url": movie.poster_url,
            "username": reviewer.username,
            "watched_on": review.review_date,
            "review_text": review.review_text,
            "movie_id": movie.id 
        })

    # You can add logic here to fetch their watched movies, reviews, etc.
    return render_template("friendProfile.html", friend=friend, my_friends=my_friends, profile_friends=profile_friends, recent_friend_movies=recent_friend_movies)

@app.route("/add-friends", methods=["GET", "POST"])
def add_friends():
    # Make sure use in session before searching for friends
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))

    query = request.args.get("query", "")
    current_user_id = session.get("user_id")
    
    users = []
    if query:
        users = User.query.filter(
            (User.username.ilike(f"%{query}%"))
        ).all()

    # IDs of people the user already follows
    followed_ids = db.session.query(Friend.friend_id).filter_by(user_id=current_user_id)

    # IDs of user’s friends
    my_friends = db.session.query(Friend.friend_id).filter_by(user_id=current_user_id).subquery()

    # Find people who are followed by friends but not the user
    # Mutual friends suggestions based on who my friends are friends with, also only get like 15
    mutual_results = (
        db.session.query(
            User,
            func.count(Friend.user_id).label("mutual_count")
        )
        .join(Friend, Friend.friend_id == User.id)
        .filter(Friend.user_id.in_(my_friends))
        .filter(~User.id.in_(followed_ids))
        .filter(User.id != current_user_id)
        .group_by(User.id)
        .order_by(func.count(Friend.user_id).desc())
        .limit(15) 
        .all()
    )

    # If mutuals < 15, fill with other users
    suggested_users = {user.id for user, _ in mutual_results}
    remaining = 15 - len(mutual_results)

    if remaining > 0:
        filler_users = (
            User.query
            .filter(
                ~User.id.in_(suggested_users),
                ~User.id.in_(followed_ids),
                User.id != current_user_id
            )
            .limit(remaining)
            .all()
        )
        mutual_results += [(user, 0) for user in filler_users]

    # Get the current friends of user
    friend_ids = db.session.query(Friend.friend_id).filter_by(user_id=current_user_id).all()
    friend_ids = [fid for (fid,) in friend_ids]

    return render_template(
        "addFriends.html",
        users=users,
        query=query,
        suggested_friends=mutual_results,
        friend_ids=friend_ids
    )
# Adds a friend by creating new relationship through users
@app.route("/send-friend-request/<int:user_id>", methods=["POST"])
def send_friend_request(user_id):
    current_user_id = session.get("user_id") 
    if current_user_id and current_user_id != user_id:
        existing = Friend.query.filter_by(user_id=current_user_id, friend_id=user_id).first()
        if not existing:
            new_friend = Friend(user_id=current_user_id, friend_id=user_id)
            db.session.add(new_friend)
            db.session.commit()
    return redirect(url_for("add_friends", query=request.args.get("query", "")))

# Removes a friend by deleting relationship
@app.route("/unfriend-request/<int:user_id>", methods=["POST"])
def unfriend_request(user_id):
    current_user_id = session.get("user_id") 
    if current_user_id and current_user_id != user_id:
        # Look for an existing friend relationship
        existing = Friend.query.filter_by(user_id=current_user_id, friend_id=user_id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
    return redirect(url_for("add_friends", query=request.args.get("query", "")))


# Movie Details
@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    reviews = Review.query.filter_by(movie_id=movie_id).all()

    movie.update_rating()

    favorite_ids = g.user.get_favorite_movies() if g.user else []
    return render_template("movie_detail.html", movie=movie, reviews=reviews, favorite_ids=favorite_ids)

@app.route("/submit_review/<int:movie_id>", methods=["POST"])
def submit_review(movie_id):
    if "user_id" not in session:
        flash("Please log in to leave a review.", "warning")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    rating = float(request.form["rating"])
    review_text = request.form["review_text"]

    # Save the review
    existing_review = Review.query.filter_by(user_id=user_id, movie_id=movie_id).first()
    movie_rating = Movie.query.filter_by(id=movie_id).first()
    if existing_review:
        existing_review.update_review(rating, review_text)
        movie_rating.update_rating()
    else:
        new_review = Review(user_id=user_id, movie_id=movie_id, rating=rating, review_text=review_text)
        db.session.add(new_review)
        movie_rating.update_rating()

    # Add to watchlist if not already there
    existing_watch = Watchlist.query.filter_by(user_id=user_id, movie_id=movie_id).first()
    if not existing_watch:
        db.session.add(Watchlist(user_id=user_id, movie_id=movie_id))

    db.session.commit()
    flash("Review submitted!", "success")
    return redirect(url_for("movie_detail", movie_id=movie_id))

@app.route("/debug-movies")
def debug_movies():
    movies = Movie.query.all()
    output = "<h1>Movie Summaries</h1><ul>"
    for movie in movies:
        output += f"<li><strong>{movie.title}</strong>: {movie.summary}</li>"
    output += "</ul>"
    return output  # This will display all movies and their summaries in your browser.

@app.route('/submit_favorites', methods=["POST"])
def submit_favorites():
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))

    favorites_data = request.form.get("favorites")
    if not favorites_data:
        flash("No favorite movies selected.", "danger")
        return redirect(url_for("dashboard"))

    new_favorites = json.loads(favorites_data)
    user = User.query.get(session["user_id"])
    
    current_favorites = set(user.get_favorite_movies())
    updated_favorites = current_favorites.union(set(new_favorites))  # Merge without duplicates

    user.set_favorite_movies(list(updated_favorites))
    db.session.commit()

    return redirect(request.referrer or url_for("dashboard"))  # Redirect back to the same page


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.args.get("query", "").strip()
    genre = request.args.get("genre", "").strip()

    results = Movie.query

    if query:
        results = results.filter(Movie.title.ilike(f"%{query}%"))

    if genre:
        results = results.filter(Movie.genre.ilike(f"%{genre}%"))

    results = results.all()

    return render_template("search.html", results=results, query=query, genre=genre)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# Home Route
@app.route("/")
def home():
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)

