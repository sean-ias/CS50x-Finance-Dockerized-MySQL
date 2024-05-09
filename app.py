import os
from flask import Flask, flash, redirect, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from sqlalchemy import text
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Read MySQL credentials from environment variables
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.session_cookie_name = "cs50"
Session(app)

# Configure CS50 Library to use MySQL database
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    hash = db.Column(db.String(255), nullable=False)
    cash = db.Column(db.Float, nullable=False, default=10000.00)

class Portfolio(db.Model):
    __tablename__ = 'portfolio'
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Integer, nullable=False, default=0)

class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    method = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Float, nullable=False)
    transacted = db.Column(db.DateTime, nullable=False, default=datetime.now)

# Create database tables
with app.app_context():
    db.create_all()

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # select user's stock portfolio and cash total
    rows = Portfolio.query.filter_by(userid=session["user_id"]).all()

    cash = User.query.filter_by(id=session["user_id"]).first()

    # get cash value float
    cash_val = cash.cash
    # this will be total value of all stock holdings and cash
    sum = cash_val

    # add stock name, add current lookup value, add total value
    for row in rows:
        look = lookup(row.symbol)
        row.price = look['price']
        row.total = row.price * row.shares

        # increment sum
        sum += row.total

        # convert price and total to usd format
        row.price = usd(row.price)
        row.total = usd(row.total)

    return render_template("index.html", rows=rows, cash=usd(cash_val), sum=usd(sum))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # if request method is GET, display buy.html form
    if request.method == "GET":
        return render_template("buy.html")

    # if request method is POST
    else:
        # save stock symbol, number of shares, and quote dict from form
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        quote = lookup(symbol)

        # return apology if symbol not provided or invalid
        if quote == None:
            return apology("must provide valid stock symbol", 403)

        # return apology if shares not provided. buy form only accepts positive integers
        if not shares:
            return apology("must provide number of shares", 403)

        # cast symbol to uppercase and cast shares to int, in order to work with them
        symbol = symbol.upper()
        shares = int(shares)
        purchase = quote['price'] * shares

        # make sure user can afford current stock, checking amount of cash in users table

        # select this user's cash balance from users table
        balance = db.session.execute(text("SELECT cash FROM users WHERE id = :id"), { "id": session["user_id"]}).fetchall()
        balance = User.query.filter_by(id=session["user_id"]).first()
        balance = balance.cash
        
        remainder = balance - purchase

        # if purchase price exceeds balance, return error
        if remainder < 0:
            return apology("insufficient funds", 403)

        # query portfolio table for row with this userid and stock symbol:
        row = db.session.execute(text("SELECT * FROM portfolio WHERE userid = :id AND symbol = :symbol"),
                         {"id": session["user_id"], "symbol": symbol}).fetchall()
        
        # if row doesn't exist yet, create it but don't update shares
        if len(row) != 1:
            portf = Portfolio(userid=session["user_id"], symbol=symbol)
            db.session.add(portf)
            db.session.commit()

        # get previous number of shares owned
        oldshares = Portfolio.query.filter_by(userid=session["user_id"], symbol=symbol).first()
        oldshares = oldshares.shares
        
        # add purchased shares to previous share number
        newshares = oldshares + shares

        # update shares in portfolio table
        portf = Portfolio.query.filter_by(userid=session["user_id"], symbol=symbol).first()
        portf.shares = newshares
        db.session.commit()

        # update cash balance in users table
        user = User.query.filter_by(id=session["user_id"]).first()
        user.cash = remainder
        db.session.commit()

        # update history table
        his = History(userid=session["user_id"], symbol=symbol, shares=shares, method='Buy', price=quote['price'])
        db.session.add(his)
        db.session.commit()

    # redirect to index page
    flash(f"Bought {shares} shares of {symbol} for {usd(purchase)}!")
    return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.session.execute(text("SELECT * FROM history WHERE userid = :userid ORDER BY transacted DESC"), {"userid": session["user_id"]}).fetchall()

    # return history template
    return render_template("history.html", rows=rows)


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
        user = User.query.filter_by(username=request.form.get("username")).first()

        # Ensure username exists and password is correct
        if not user or not check_password_hash(
            user.hash, request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = user.id

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # if GET method, return quote.html form
    if request.method == "GET":
        return render_template("quote.html")

    # if POST method, get info from form, make sure it's a valid stock
    else:

        # lookup ticker symbol from quote.html form
        symbol = lookup(request.form.get("symbol"))

        # if lookup() returns None, it's not a valid stock symbol
        if symbol == None:
            return apology("invalid stock symbol", 403)

        # Return template with stock quote, passing in symbol dict
        return render_template("quote.html", quote=symbol)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (submitting the register form)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # ensure passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 403)

        # save username and password hash in variables
        username = request.form.get("username")
        hash = generate_password_hash(request.form.get("password"))

        # Query database to ensure username isn't already taken
        rows = db.session.execute(text("SELECT * FROM users WHERE username = :username"), { "username": username }).fetchall()
        if len(rows) != 0:
            return apology("username is already taken", 403)

        # insert username and hash into database
        user = User(username=username, hash=hash)
        db.session.add(user)
        db.session.commit()

        # redirect to login page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # if GET method, render sell.html form
    if request.method == "GET":

        # get the user's current stocks
        portfolio = db.session.execute(text("SELECT symbol FROM portfolio WHERE userid = :id"),
                               {"id": session["user_id"]}).fetchall()

        # render sell.html form, passing in current stocks
        return render_template("sell.html", portfolio=portfolio)

    # if POST method, sell stock
    else:
        # save stock symbol, number of shares, and quote dict from form
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        quote = lookup(symbol)
        rows = Portfolio.query.filter_by(userid=session["user_id"], symbol=symbol).first()

        # return apology if symbol invalid/ not owned
        if not rows:
            return apology("must provide valid stock symbol", 403)

        # return apology if shares not provided. buy form only accepts positive integers
        if not shares or not shares.isdigit() or int(shares)<=0:
            return apology("must provide number of shares", 403)

        # current shares of this stock
        oldshares = rows.shares

        # cast shares from form to int
        shares = int(shares)

        # return apology if trying to sell more shares than own
        if shares > oldshares:
            return apology("shares sold can't exceed shares owned", 403)

        # get current value of stock price times shares
        sold = quote['price'] * shares

        # add value of sold stocks to previous cash balance
        cash = User.query.filter_by(id=session['user_id']).first()
        cash = cash.cash
        cash = cash + sold

        # update cash balance in users table
        user = User.query.filter_by(id=session["user_id"]).first()
        user.cash = cash
        db.session.commit()

        # subtract sold shares from previous shares
        newshares = oldshares - shares

        # if shares remain, update portfolio table with new shares
        if shares > 0:
            portf = Portfolio.query.filter_by(userid=session["user_id"], symbol=symbol).first()
            portf.shares = newshares
            db.session.commit()

        # otherwise delete stock row because no shares remain
        else:
            portf = Portfolio.query.filter_by(userid=session["user_id"], symbol=symbol).first()
            db.session.delete(portf)
            db.session.commit()


        # update history table
        his=History(userid=session["user_id"], symbol=symbol, shares=-shares, method='Sell', price=quote['price'])
        db.session.add(his)
        db.session.commit()
        
        # redirect to index page
        flash(f"Sold {shares} shares of {symbol} for {usd(sold)}!")
        return redirect("/")
    
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)