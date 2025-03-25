import os
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, login_required, lookup, usd
from datetime import datetime
from cs50 import SQL



app = Flask(__name__)

app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)




db = SQL("sqlite:///scenario1.db")

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    progress = db.execute("SELECT Level FROM users WHERE User_ID = :id", id=session["user_id"])
    return render_template("curriculum_1.html", progress = progress)

@app.route("/next", methods=["GET", "POST"])
@login_required
def next_level():
    user_id = session["user_id"]
    # Get current level from the database
    rows = db.execute("SELECT Level FROM users WHERE User_ID = ?", user_id)
    if len(rows) != 1:
        return apology("user not found", 403)

    current_level = int(rows[0]["Level"])

    # Validate that the level is less than the max level (assumed 3)
    if current_level < 3:
        new_level = current_level + 1
        db.execute("UPDATE users SET Level = ? WHERE User_ID = ?", new_level, user_id)
    # Otherwise, perhaps mark the curriculum as complete or just redirect
    return redirect("/curriculum")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE user_name = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password_hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["User_ID"]
        
        # Redirect user to home page
        return redirect("/curriculum")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/curriculum")
@login_required
def curriculum():
    user_id = session["user_id"]
    rows = db.execute("SELECT Level, Curriculum FROM users WHERE User_ID = ?", user_id)
    if len(rows) != 1:
        return apology("User not found", 403)
    current_level = int(rows[0]["Level"])  # convert to integer if needed
    curriculum_val = rows[0]["Curriculum"]

    return render_template("curriculum_1.html", level=current_level, curriculum=curriculum_val)

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")







@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)
        row = db.execute("SELECT user_name FROM users")
        for i in range(len(row)):
            if request.form.get("username") == row[i]["user_name"]:
                return apology("username already exists", 400)
        if not request.form.get("password") or not request.form.get("confirmation") or request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords do not match", 400)
        if not request.form.get("age"):
            return apology("Enter your age", 400)
        username = request.form.get("username")
        password = request.form.get("password")
        age = request.form.get("age")
        if int(age) > int(15):
            curr = 2 
        else:
            curr = 1
        db.execute("INSERT INTO users (user_name, password_hash, age, Level, Curriculum) VALUES(?, ?, ?, 1, ?)", username,
                   generate_password_hash(password, method='pbkdf2', salt_length=16), age, curr)
        return redirect("/login")

    else:
        return render_template("register.html")



