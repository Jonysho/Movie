import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, get_all, lookupId

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

#THIS IS TMDB API KEY
#export API_KEY=61fa968ea1f32237a597a9cd500d9eea

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

#Recommend popular movies
@app.route("/")
@login_required
def index():
    results = get_all()
    trend = results[0]
    upcoming = results[1]
    tvpop = results[2]
    return render_template("index.html", trend=trend, upcoming=upcoming, tvpop=tvpop)

#Add movie to personal ranking
@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    user_id = session["user_id"]
    if request.method == "POST":
        if not request.form.get("title"):
            return apology("Missing title", 400)
        rating = request.form.get("rating")
        if not rating:
            return apology("Missing rating", 400)
        rating = round(float(request.form.get("rating")), 1)

        keyword = request.form.get("title")
        type = request.form.get("type")
        isId = request.form.get("show_id")
        print(isId)
        if isId == "show_id":
            show = lookupId(keyword, type)
        else:
            show = lookup(keyword, type, 1)
        # Check if show is valid or already in db
        if not show:
            return apology("Invalid title", 400)
        if not isId:
            show = show[0]
        userList = db.execute("SELECT title FROM list WHERE user_id = ?", user_id)

        title = show["title"]
        for each in userList:
            if title == each["title"]:
                return apology("Show already in list", 400)

        # Check if rating is valid i.e. 0-10
        if rating < 0.0 or rating > 10.0:
            return apology("Invalid rating", 400)
        else:
            imageURL = "https://image.tmdb.org/t/p/w45/"+show["image"]
            show_id = show["id"]
            db.execute("INSERT INTO list (show_id, title, image, rating, user_id) VALUES (?, ?, ?, ?, ?)", show_id, title, imageURL, rating, user_id)
            statUpdate(show_id, type, user_id, title)
            return redirect("/mylist")
    else:
        return render_template("add.html")

# Update user stats db
def statUpdate(show_id, type, user_id, title):
    # get details of show being added
    show = lookupId(show_id, type)
    eps = show["eps"]
    runtime = show["runtime"]
    total_runtime = eps*runtime
    # get current stats from table stats in db
    stats = db.execute("SELECT * FROM stats WHERE user_id = ?", user_id)
    print(stats)
    if not stats:
        db.execute("INSERT INTO stats (user_id) VALUES (?)", user_id)
        stats = db.execute("SELECT * FROM stats WHERE user_id = ?", user_id)
    stats = stats[0]
    if type == "mv":
        if total_runtime > stats["mv_mins"]:
            db.execute("UPDATE stats SET mv_mins = ?, mv = ?, total_mv_mins = ? WHERE user_id = ?", total_runtime, title, stats["total_mv_mins"]+total_runtime, user_id)
    if type == "tv":
        if total_runtime > int(stats["tvshow_mins"]):
            db.execute("UPDATE stats SET tvshow_mins = ?, tvshow = ?, eps = ?, total_tv_mins = ? WHERE user_id = ?", total_runtime, title, eps, stats["total_tv_mins"]+total_runtime, user_id)
    db.execute("UPDATE stats SET total_mins = ? WHERE user_id = ?", stats["total_mins"] + total_runtime, user_id)

#Show personal ranking of shows
@app.route("/mylist")
@login_required
def mylist():
    #rank, image, title, rating
    user_id = session["user_id"]
    # Get list of shows and sort them in desc
    shows = db.execute("SELECT * FROM list WHERE user_id = ? ORDER BY rating DESC", user_id)
    if not shows:
        return apology("No list avaliable")
    updateRank(shows)
    shows = db.execute("SELECT * FROM list WHERE user_id = ? ORDER BY rating DESC", user_id)
    return render_template("mylist.html", shows=shows)

#Show user stats
@app.route("/mystats")
@login_required
def myStats():
    user_id = session["user_id"]
    # Get list of shows and sort them in desc
    stats = db.execute("SELECT * FROM stats WHERE user_id = ?", user_id)
    if not stats:
        return apology("No stats avaliable")
        #mv_mins = stats["mv_mins"]
        #mv = stats["mv"]
        #tvshow_mins = stats["tv]
    return render_template("stats.html", stats=stats[0])

#Update rankings in db using ordered list
def updateRank(oL):
    #for each show in the list
    for show in oL:
        #change the rank to the index+1 in the db
        i = oL.index(show)+1
        db.execute("UPDATE list SET rank = ? WHERE  id = ?", i, show["id"])

#Return public rating
@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    if request.method == "POST":
        keyword = request.form.get("title")
        if not keyword:
            return apology("Enter a title", 400)
        else:
            shows = lookup(keyword, request.form.get("type"), int(request.form.get("num")))
            if not shows:
                return apology("No results", 400)
            else:
                imageURL = "https://image.tmdb.org/t/p/w300/"
                return render_template("searched.html", shows=shows, imageURL=imageURL)
    else:
        return render_template("search.html")

#Edit ranking
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    return redirect("/")

#LOGIN
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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

#LOGOUT
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

#REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # Ensure username was submitted
        if not username:
            return apology("must provide username", 400)

        # Ensure username does not already
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 0:
            return apology("username already exists", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 400)

        # Ensure both passwords match

        elif password != confirmation:
            return apology("passwords do not match", 400)

        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")



