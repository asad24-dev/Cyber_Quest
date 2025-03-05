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

global currentname

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///scenario1.db"
# db = SQLAlchemy(app)
# db = SQL("sqlite:///project.db")
db = SQL("sqlite:///scenario1.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    portfolio = db.execute("SELECT users.Username FROM users, friend WHERE friend.User_ID = :id AND users.User_ID = friend.Friend_ID", id=session["user_id"])
    return render_template("curriculum_1.html", portfolio = portfolio)

@app.route("/curriculum1")
def curriculum_1():
    return render_template('curriculum_1.html')

@app.route("/sent")
@login_required
def sent():
    sentmsg = db.execute("SELECT * FROM message_sent WHERE User_ID = :id ORDER BY Date", id = session["user_id"])
    return render_template("sent.html", sentmsg = sentmsg)

@app.route("/rec")
@login_required
def rec():
    recmsg = db.execute("SELECT * FROM message_rec WHERE User_ID = :id ORDER BY Date", id = session["user_id"])
    return render_template("rec.html", recmsg = recmsg)

@app.route("/chat", methods = ["GET"])
@login_required
def chat():
    global currentname
    currentname = request.args.get("currentname")
    if request.method == "GET":
        return render_template("chat.html", currentname = currentname)

@app.route("/msgsent", methods = ["GET"])
@login_required
def msgsent():
    global currentname
    if request.method == "GET":
        unread = 0
        currentname = request.args.get("currname")
        currid = db.execute("SELECT User_ID FROM users WHERE Username = :name", name = currentname)
        curr = currid[0]['User_ID']
        message = request.args.get("message")
        datetimes = datetime.now()
        date = datetimes.date()
        timemsg = datetimes.time()
        user = session["user_id"]
        username = db.execute("SELECT Username FROM users WHERE User_ID = :id", id = session["user_id"])
        name = username[0]['Username']
        db.execute("INSERT INTO message_sent (Friend_ID, User_ID, message, Date, Friend_Name, Time) VALUES(?, ?, ?, ?, ?, ?)", curr, user , message, date, currentname, timemsg)
        db.execute("INSERT INTO message_rec (Friend_ID, User_ID, message, Date, Friend_Name, Time) VALUES(?, ?, ?, ?, ?, ?)", user, curr, message, date, name, timemsg)
        flash("Sent!")
        unread += 1
        return redirect("/")


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
        rows = db.execute("SELECT * FROM users WHERE Username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
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


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    if request.method == "POST":
        name = request.form.get("name")
        a = True
        searchid = db.execute("SELECT User_ID, Username FROM users WHERE Username = :name", name = name)
        friend = db.execute("SELECT users.Username from users, friend WHERE friend.User_ID = :uid", uid = session["user_id"])
        if not searchid:
            return apology("name not Found", 400)
        return render_template("searched.html", searchid = searchid, friend = friend, a = a)

    else:
        return render_template("search.html")

@app.route("/friend", methods=["POST"])
@login_required
def friend():
    currentid = request.form.get("currentid")
    db.execute("INSERT INTO friend (User_ID, Friend_ID) VALUES(?, ?)", session["user_id"], currentid )
    db.execute("INSERT INTO friend (User_ID, Friend_ID) VALUES(?, ?)", currentid, session["user_id"])
    flash("ADDED")
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

        username = request.form.get("username")
        password = request.form.get("password")
        age = request.form.get("age")
        db.execute("INSERT INTO users (user_name, password_hash, age, Level) VALUES(?, ?, ?, 0)", username,
                   generate_password_hash(password, method='pbkdf2', salt_length=16), age)
        return redirect("/login")

    else:
        return render_template("register.html")



