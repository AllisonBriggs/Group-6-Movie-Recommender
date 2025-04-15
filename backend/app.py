from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from sqlalchemy.sql.expression import func 
import os
import json

# Import models AFTER db initialization
from models import db, User, Movie

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

        # Hash the password using set_password()
        new_user = User(username=username, password=password, favorite_genres=null)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

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

# Dashboard (Accessible After Login)
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        selected_genres = request.form.getlist("genre")

        if len(selected_genres) == 0:
            flash("Please select at least one genre.", "danger")
            return redirect(url_for("dashboard"))

        if len(selected_genres) > 3:
            flash("You can select up to 3 genres.", "danger")
            return redirect(url_for("dashboard"))

        # Save genres to the user profile
        user.set_favorite_genres(selected_genres)

        flash("Genres updated successfully!", "success")
        return redirect(url_for("dashboard"))

    # Get previously saved genres
    selected_genres = user.get_favorite_genres()

    # Fetch random movies based on stored genres
    recommended_movies = {}
    for genre in selected_genres:
        movies = Movie.query.filter(Movie.genre.ilike(f"%{genre}%")).order_by(func.random()).limit(5).all()
        recommended_movies[genre] = movies

    return render_template("dashboard.html", movies=recommended_movies, selected_genres=selected_genres, username=g.user.username)
# Acount Route
@app.route("/profile")
def profile():
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("login"))
    
    return render_template("profile.html", username=g.user.username)

# Movie Details
@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)  # Fetch movie or return 404 if not found

    return render_template("movie_detail.html", movie=movie)

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

    flash("Movies updated successfully!", "success")
    return redirect(url_for("dashboard"))

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

