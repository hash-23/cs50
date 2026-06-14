import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps
from cs50 import SQL

db = SQL("sqlite:///tutoring.db")

def apology(message, code=400, page=""):
    """Render message as an apology to user."""
    return render_template("apology.html", top=code, message=message, back=page), code

def success(message, page=""):
    return render_template("success.html", message=message, back=page)

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def validate_register(username, email, password, confirm, fname, sname):
    #one input is missing
        if not username or not email or not password or not confirm or not fname or not sname:
            return ("Please fill in all fields")

        #password and confirm do not match
        if password != confirm:
            return ("Password and confirmation do not match")

        #checking if user already exists
        username_exists = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(username_exists) > 0:
            return ("Username is already in use")

        email_exists = db.execute("SELECT * FROM users WHERE email = ?", email)
        if len(email_exists) > 0:
            return ("Email is already in use")

        #no issues
        return ("")