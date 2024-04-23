from functools import wraps

from flask import g, request


def extract_data(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json()
        g.conversation_id = data["conversation"]["id"]
        g.from_field = data["latest_message"]["from_field"]
        g.to_fields = data["latest_message"]["to_fields"]
        return f(*args, **kwargs)

    return decorated_function
