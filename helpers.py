import requests

from flask import redirect, render_template, session
from functools import wraps


# checked if login has been passed. 
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


# declared teh values into GBP currency with 2 dec place
# @app.template_filter('gbp')
def gbp(value):
    """Format value as GBP"""
    if value is None:
        return 0
    return f"£{value:,.1f}"

# formual to round up to 0.5 days.

def round_to_half(value):
    if value is None:
        return 0
    return (round(value * 2) / 2)

