from flask import Flask, request
import random
from db_handler import DbHandler

DB_HANDLER: DbHandler | None = None

def set_databast_handler(handler: DbHandler = DbHandler()):
    global DB_HANDLER
    DB_HANDLER = handler

app = Flask(__name__)
app.url_map.strict_slashes = False

@app.after_request
def add_headers(response):
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Headers'] = "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With"
    response.headers['Access-Control-Allow-Methods'] = "POST, GET, PUT, DELETE"
    return response



@app.route("/<user_email>", methods=["GET","POST"])
def get_user(user_email: str) -> tuple[str, int]:
    """
    Handles the base account endpoint.

    GET requests return a random phrase from the user's 8 ball.
    If the user didn't already have one, one is created for them with default phrases.

    POST requests create an account with the given email.
    """
    if request.method == "POST": 
        if DB_HANDLER.add_user(user_email) is None: 
            return ("Could not create account", 404)   
        else: 
            return ("Account created", 200)

    array = ["ResponseYes", "ResponseNo", "ResponseUnknown"]
    category = array[random.randrange(0,3)]
    return get_ball_response(user_email, category)

@app.route("/<user_email>/all", methods=["GET", "PUT", "DELETE"])
def all_answers(user_email: str) -> tuple[str | dict[str, list[str]], int]:
    """
    Handles the "all" endpoint.

    GET requests return a JSON of every phrase in the user's 8ball
    If the user didn't already have one, one is created for them with default phrases.

    PUT requests append user-provided phrases to their 8-ball's lists.
    If the user didn't already have one, one is created for them, with the only phrases being the ones provided in this call.

    DELETE requests erase the user's 8-ball entirely.
    """
    if request.method == "GET": return get_ball_response(user_email)
    if request.method == "PUT": return add_phrases(user_email)
    if DB_HANDLER.delete_ball(user_email):
        return ("Ball deleted", 200)
    else:
        return ("No such account", 404)

@app.route("/<user_email>/yes", methods=["GET", "DELETE"])
def all_yes(user_email: str) -> tuple[str | dict[str, list[str]], int]:
    """
    Handles the "yes" endpoint.

    GET requests return a JSON of every phrase in the Yes category of the user's 8ball
    If the user didn't already have one, one is created for them with default phrases.

    DELETE requests erase all Yes answers in the user's 8ball
    """
    if request.method == "GET": return get_ball_response(user_email, ["ResponseYes"])
    if DB_HANDLER.delete_answers(user_email, "ResponseYes"):
        return ('"Yes" answers deleted', 200)
    else:
        return ("No such account", 404)

@app.route("/<user_email>/no", methods=["GET", "DELETE"])
def all_no(user_email: str) -> tuple[str | dict[str, list[str]], int]:
    """
    Handles the "no" endpoint.

    GET requests return a JSON of every phrase in the No category of the user's 8ball
    If the user didn't already have one, one is created for them with default phrases.

    DELETE requests erase all Yes answers in the user's 8ball
    """
    if request.method == "GET": return get_ball_response(user_email, ["ResponseNo"])
    if DB_HANDLER.delete_answers(user_email, "ResponseNo"):
        return ('"No" answers deleted', 200)
    else:
        return ("No such account", 404)

@app.route("/<user_email>/unknown", methods=["GET", "DELETE"])
def all_unknown(user_email: str) -> tuple[str | dict[str, list[str]], int]:
    """
    Handles the "unknown" endpoint.

    GET requests return a JSON of every phrase in the Unknown category of the user's 8ball
    If the user didn't already have one, one is created for them with default phrases.

    DELETE requests erase all No answers in the user's 8ball
    """
    if request.method == "GET": return get_ball_response(user_email, ["ResponseUnknown"])
    if DB_HANDLER.delete_answers(user_email, "ResponseUnknown"):
        return ('"Unknown" answers deleted', 200)
    else:
        return ("No such account", 404)

def get_ball_response(user_email: str, properties: str | list[str] = ["ResponseYes", "ResponseNo", "ResponseUnknown"]) -> tuple[str | dict[str, list[str]], int]:
    """
    General function for sending phrases to a given user.

    The main data of the return value depends on if a string or a list was passed to the properties parameter

    If a list is provided, then a dictionary of lists (keyed by answer category) will be returned containing every answer for each requested category.
    
    If a string is provided, then a randomly chosen string from the provided category is returned.
    """ 
    give_single_response = isinstance(properties, str)
    if give_single_response: properties = [properties]

    data = DB_HANDLER.get_answers(user_email, properties)
    if data is None: return ("Account does not exist for this email", 404)

    if give_single_response:
        array = data[0]
        if array is None: 
            answer = properties[0].removeprefix("Response")
        else:
            length = len(array)
            answer = array[random.randrange(0,length)]
        return (answer, 200)
    
    send = dict()
    for i in range(0, len(properties)):
        key = properties[i].removeprefix("Response")
        array = data[i]
        send[key] = [] if array is None else array
    return (send, 200)

def add_phrases(user_email: str) -> tuple[str | dict[str, list[str]], int]:
    """
    Function for adding phrases from a given user.

    The main data of the return value depends on if parsing the user-sent JSON body was successful

    If it was successful, then a dictionary of lists (keyed by answer category) will be returned containing every successfully inserted phrase.
    
    If not, an error string is returned.
    """ 
    object: dict[str, str | list[str]] = request.get_json(silent=True, force=True)
    if (object is None):
        return ("Parsing Error", 404)
    
    additions = dict()

    for key in ["Yes","No","Unknown"]:
        data = object.get(key)
        if (data is None): continue
        if (isinstance(data, str)):
            data = [data]
        additions["Response" + key] = data
    
    response = DB_HANDLER.add_answers(user_email, additions)
    if (response is None):
        return ("Something went wrong with adding the answers", 404)
    return (response, 200)


if __name__ == "__main__":
    set_databast_handler()
    app.run(host='0.0.0.0')
