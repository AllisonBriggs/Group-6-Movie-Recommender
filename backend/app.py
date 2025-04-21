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
    # Get previously saved genres
    selected_genres = user.get_favorite_genres()

    recommender = Recommendation(user, db)
    recommended_movies_list = recommender.rec_by_genre()

    # Group movies by genre for display
    recommended_movies = {}
    for movie in recommended_movies_list:
        for genre in user.get_favorite_genres():
            if genre.lower() in movie.genre.lower():
                recommended_movies.setdefault(genre, []).append(movie)
                break

    return render_template("dashboard.html",
                       username=user.username,
                       selected_genres=selected_genres,
                       movies=recommended_movies)

# Acount Route
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    selected_genres = user.get_favorite_genres()
    
    
    return render_template("profile.html", username=user.username, selected_genres=selected_genres)

@app.route("/friends", methods=["GET", "POST"])
def friends():
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    query = request.args.get("query", "")
    
    users = []
    if query:
        users = User.query.filter(
            (User.username.ilike(f"%{query}%"))
        ).all()
    


    # Get the current friends of user 
    friend_ids = (
    db.session.query(Friend.friend_id)
    .filter_by(user_id=user.id)
    .all()
    )
    friend_ids = [fid for (fid,) in friend_ids]

    friends = User.query.filter(User.id.in_(friend_ids)).all()

    # Get the current followers of user
    follower_ids = (
    db.session.query(Friend.user_id)
    .filter_by(friend_id=user.id)
    .all()
    )
    follower_ids = [fid for (fid,) in follower_ids]

    followers = User.query.filter(User.id.in_(follower_ids)).all()

    print(friend_ids)
    return render_template("friends.html", username=user.username, users=users, query=query, friends=friends, followers=followers)

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
    return render_template("movie_detail.html", movie=movie, reviews=reviews)

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
    if existing_review:
        existing_review.update_review(rating, review_text)
    else:
        new_review = Review(user_id=user_id, movie_id=movie_id, rating=rating, review_text=review_text)
        db.session.add(new_review)

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
    
    favorites = json.loads(favorites_data)

    user = User.query.get(session["user_id"])

    user.set_favorite_movies(favorites)
    db.session.commit()  

    #flash("Movies updated successfully!", "success")
    return redirect(url_for("home"))

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

