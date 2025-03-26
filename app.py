import os
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, login_required, lookup, usd
from datetime import datetime
from cs50 import SQL
import random
from random import choice



app = Flask(__name__)

app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)




db = SQL("sqlite:///scenario1.db")

def init_db():
    db.execute("""
        CREATE TABLE IF NOT EXISTS ai_game_progress (
            user_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            total_attempts INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(User_ID)
        )
    """)

# Call init_db immediately after defining it
init_db()

# Store image data - you'll need to update these paths based on your structure
IMAGES = [
    {"filename": "AI_landscape.png", "is_ai": True, "level": 1},
    {"filename": "AI_person.png", "is_ai": True, "level": 1},
    {"filename": "Real_landscape.jpg", "is_ai": False, "level": 1},
    {"filename": "Real_person.png", "is_ai": False, "level": 1}
]

def get_unseen_image(level, seen_images):
    """Get a random unseen image for the given level"""
    level_images = [img for img in IMAGES if img["level"] == level]
    unseen_images = [img for img in level_images if img["filename"] not in seen_images]
    
    # If all images have been seen, reset the seen images
    if not unseen_images:
        seen_images.clear()
        unseen_images = level_images
    
    return choice(unseen_images)


@app.route("/")
@login_required
def index():
    """Show main dashboard"""
    user_id = session["user_id"]
    rows = db.execute("SELECT Level, Curriculum FROM users WHERE User_ID = ?", user_id)
    if len(rows) != 1:
        return apology("User not found", 403)
    return redirect(url_for('curriculum'))

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
    return render_template("curriculum_1.html", level=current_level, curriculum=curriculum_val, article_read = article_read, quiz_passed = quiz_passed)

@app.route("/game/<int:level>", methods=["GET", "POST"])
@login_required
def game(level):
    user_id = session["user_id"]
    # Retrieve user's curriculum from their record
    # Retrieve user's curriculum from the users table.
    rows = db.execute("SELECT Curriculum FROM users WHERE User_ID = ?", user_id)
    if len(rows) != 1:
        return apology("User not found", 403)
    curriculum_val = rows[0]["Curriculum"]

    # Retrieve quiz questions for the given curriculum and level.
    questions = db.execute("SELECT * FROM quiz_questions WHERE curriculum = ? AND level = ?",
                        curriculum_val, level)
    # (Optionally, you might want to check if questions is empty and handle that case.)

    if request.method == "POST":
        score = 0
        total = len(questions)
        wrong = []  # store question ids for which the answer was wrong.

        # Loop over questions and check each answer from the submitted form.
        for q in questions:
            ans = request.form.get("question_" + str(q["id"]))
            if ans is not None and int(ans) == q["correct_option"]:
                score += (1 / total) * 100
                progress = db.execute("SELECT * FROM quiz_progress WHERE user_id = ? AND curriculum = ? AND level = ?", user_id, curriculum_val, level)
                if len(progress) == 0:
                    db.execute("INSERT INTO quiz_progress (user_id, curriculum, level, game_passed) VALUES (?, ?, ?, 1)", user_id, curriculum_val, level)
                else:
                    db.execute("UPDATE quiz_progress SET game_passed = 1 WHERE user_id = ? AND curriculum = ? AND level = ?", user_id, curriculum_val, level)
            else:
                wrong.append(q["id"])

        # Always return a response. If score calculation is done, render the result page.
        return render_template("game_result.html", level=level, score=score, total=total, wrong=wrong)

    elif request.method == "GET":
        # For GET method, render the quiz page.
        return render_template("game.html", level=level, quiz_questions=questions)

    # As a fallback, if neither GET nor POST (should not happen normally), return an error.
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

@app.route("/play")
@login_required
def play():
    # Select random image
    if not session.get("current_image"):
        session["current_image"] = random.choice(IMAGES)
    return render_template("play.html", image=session["current_image"])

@app.route("/guess", methods=["POST"])
@login_required
def guess():
    guess = request.form.get("guess") == "true"
    current_image = session["current_image"]
    
    is_correct = guess == current_image["is_ai"]
    
    if is_correct:
        session["score"] = session.get("score", 0) + 1
    session["total"] = session.get("total", 0) + 1
    
    session["current_image"] = None
    
    return render_template("result.html", 
                         is_correct=is_correct,
                         image=current_image,
                         score=session["score"],
                         total=session["total"])

@app.route("/ai_game/<int:level>", methods=["GET"])
@login_required
def ai_game(level):
    try:
        user_id = session["user_id"]
        
        # Get user's progress
        progress = db.execute("SELECT score, total_attempts FROM ai_game_progress WHERE user_id = ?", user_id)
        if not progress:
            db.execute("INSERT INTO ai_game_progress (user_id, score, total_attempts) VALUES (?, 0, 0)", user_id)
            progress = [{"score": 0, "total_attempts": 0}]
        
        # Reset game score for this session
        session["score"] = 0
        session["total"] = 0
        session["seen_images"] = [] 
        
        # Get user's progress
        progress = db.execute("SELECT score, total_attempts FROM ai_game_progress WHERE user_id = ?", user_id)
        if not progress:
            db.execute("INSERT INTO ai_game_progress (user_id, score, total_attempts) VALUES (?, 0, 0)", user_id)
            progress = [{"score": 0, "total_attempts": 0}]
        
        return render_template("ai_game.html", 
                             level=level,
                             total_score=progress[0]["score"],
                             total_attempts=progress[0]["total_attempts"])
    except Exception as e:
        print(f"Error in ai_game route: {str(e)}")
        return apology(f"An error occurred: {str(e)}", 500)

@app.route("/ai_play/<int:level>")
@login_required
def ai_play(level):
    # Initialize or get the list of seen images for this session
    if "seen_images" not in session:
        session["seen_images"] = []
    
    # Select random unseen image for this level
    if not session.get("current_image"):
        current_image = get_unseen_image(level, session["seen_images"])
        session["current_image"] = current_image
        session["seen_images"].append(current_image["filename"])
    
    return render_template("play.html", image=session["current_image"], level=level)

@app.route("/ai_guess/<int:level>", methods=["POST"])
@login_required
def ai_guess(level):
    user_id = session["user_id"]
    guess = request.form.get("guess") == "true"
    current_image = session["current_image"]
    
    is_correct = guess == current_image["is_ai"]
    
    # Update session score
    if is_correct:
        session["score"] = session.get("score", 0) + 1
    session["total"] = session.get("total", 0) + 1
    
    # Update database score
    db.execute("""
        UPDATE ai_game_progress 
        SET score = score + ?, total_attempts = total_attempts + 1 
        WHERE user_id = ?
    """, 1 if is_correct else 0, user_id)
    
    # Clear current image for next round
    session["current_image"] = None
    
    # If they've completed enough correct guesses, mark the level as passed
    if session["score"] >= 3:  # Require 3 correct answers to pass
        progress = db.execute(
            "SELECT * FROM quiz_progress WHERE user_id = ? AND curriculum = ? AND level = ?", 
            user_id, 'ai_game', level
        )
        if len(progress) == 0:
            db.execute(
                "INSERT INTO quiz_progress (user_id, curriculum, level, game_passed) VALUES (?, ?, ?, 1)", 
                user_id, 'ai_game', level
            )
        else:
            db.execute(
                "UPDATE quiz_progress SET game_passed = 1 WHERE user_id = ? AND curriculum = ? AND level = ?", 
                user_id, 'ai_game', level
            )
    
    return render_template("result.html",
                         is_correct=is_correct,
                         image=current_image,
                         score=session["score"],
                         total=session["total"],
                         level=level)

if __name__ == "__main__":
    app.run(debug=True)



