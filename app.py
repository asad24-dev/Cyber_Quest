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
    info = db.execute("SELECT * FROM users WHERE user_id = ?", session["user_id"])
    if len(info) != 1:
        return apology("User not found", 403)
    username = info[0]["user_name"]
    level = info[0]["Level"]
    progress = (((level - 1) / 3) * 100)
    curriculum = info[0]["Curriculum"]
    tech_quote = "The first 1GB hard drive was announced in 1980 and weighed over 500 pounds."
    return render_template("home.html", username = username, progress=progress, level=level, curriculum=curriculum, tech_quote=tech_quote)

@app.route("/curriculum")
@login_required
def curriculum():
    user_id = session["user_id"]
    rows = db.execute("SELECT Level, Curriculum FROM users WHERE User_ID = ?", user_id)
    if len(rows) != 1:
        return apology("User not found", 403)
    current_level = int(rows[0]["Level"])  # convert to integer if needed
    curriculum_val = rows[0]["Curriculum"]
    progress = db.execute("SELECT ap.article_read FROM articles AS a LEFT JOIN article_progress AS ap ON a.id = ap.article_id AND ap.user_id = ? WHERE a.curriculum = ? AND a.level = ?", user_id, curriculum_val, current_level)
    article_read = (len(progress) == 1 and progress[0]["article_read"] == 1)
    progress_quiz = db.execute("SELECT game_passed FROM quiz_progress WHERE user_id = ? AND curriculum = ? AND level = ?", user_id, curriculum_val, current_level)
    quiz_passed = (len(progress_quiz) == 1 and progress_quiz[0]["game_passed"] == 1)
    if curriculum_val == 1:
        return render_template("curriculum_1.html", level=current_level, curriculum=curriculum_val, article_read = article_read, quiz_passed = quiz_passed)
    else:
        return render_template("curriculum_2.html", level=current_level, curriculum=curriculum_val, article_read = article_read, quiz_passed = quiz_passed)

@app.route("/game/<int:level>", methods=["GET", "POST"])
@login_required
def game(level):
    user_id = session["user_id"]
    # Retrieve user's curriculum from the users table
    rows = db.execute("SELECT Curriculum FROM users WHERE User_ID = ?", user_id)
    if len(rows) != 1:
        return apology("User not found", 403)
    curriculum_val = rows[0]["Curriculum"]

    # Retrieve quiz questions
    questions = db.execute("SELECT * FROM quiz_questions WHERE curriculum = ? AND level = ?",
                        curriculum_val, level)
    
    if len(questions) == 0:
        return apology("No questions found for this level", 404)

    if request.method == "POST":
        score = 0
        total = len(questions)
        wrong = []
        
        # Check if we have a final score from the timed quiz
        final_score = request.form.get("final_score")
        if final_score and final_score.isdigit():
            score = int(final_score)
        else:
            # Fallback to original scoring system
            for q in questions:
                ans = request.form.get("question_" + str(q["id"]))
                if ans is not None and int(ans) == q["correct_option"]:
                    score += (1 / total) * 100
                else:
                    wrong.append(q["id"])
        
        # Record quiz progress regardless of scoring method
        progress = db.execute("SELECT * FROM quiz_progress WHERE user_id = ? AND curriculum = ? AND level = ?", 
                            user_id, curriculum_val, level)
        
        # Mark as passed if score is at least 70%
        passed = score >= 70
        
        if len(progress) == 0:
            db.execute("INSERT INTO quiz_progress (user_id, curriculum, level, game_passed, score) VALUES (?, ?, ?, ?, ?)", 
                    user_id, curriculum_val, level, 1 if passed else 0, score)
        else:
            db.execute("UPDATE quiz_progress SET game_passed = ?, score = ? WHERE user_id = ? AND curriculum = ? AND level = ?", 
                    1 if passed else 0, score, user_id, curriculum_val, level)

        return render_template("game_result.html", level=level, score=score, total=total, wrong=wrong, passed=passed)

    elif request.method == "GET":
        return render_template("game.html", level=level, quiz_questions=questions)

    return apology("Invalid request method", 400)
            

@app.route("/article/<int:level>", methods=["GET", "POST"])
@login_required
def article(level):
    user_id = session["user_id"]
    rows = db.execute("SELECT Curriculum FROM users WHERE User_ID = ?", user_id)
    if len(rows) != 1:
        return apology("User not found", 403)
    curriculum_val = rows[0]["Curriculum"]

    # Query the article based on curriculum and level.
    result = db.execute("SELECT * FROM articles WHERE curriculum = ? AND level = ?", curriculum_val, level)
    if len(result) != 1:
        return apology("Article not found", 404)
    article = result[0]

    if request.method == "POST":
        # Mark the article as read in the article_progress table.
        progress = db.execute("SELECT * FROM article_progress WHERE user_id = ? AND article_id = ?", user_id, article["id"])
        if len(progress) == 0:
            db.execute("INSERT INTO article_progress (user_id, article_id, article_read) VALUES (?, ?, 1)", user_id, article["id"])
        else:
            db.execute("UPDATE article_progress SET article_read = 1 WHERE user_id = ? AND article_id = ?", user_id, article["id"])
        return redirect("/curriculum")
    else:
        return render_template("article.html", level=level, article=article)
    
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
    else:
        return render_template("complete.html")
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
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")



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



