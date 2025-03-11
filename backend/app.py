from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os

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
        new_user = User(username=username, password=password)
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

    movies = Movie.query.all()  # Fetch all movies from the database
    print("Movies in DB:", movies)  # Debugging: Check if movies exist

    return render_template("dashboard.html", movies=movies, username=g.user.username)
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

# Home Route
@app.route("/")
def home():
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)

