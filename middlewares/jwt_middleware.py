import os

from dotenv import load_dotenv
from flask import request

from exceptions import APIException

load_dotenv(override=True)
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


class AuthMiddleware:
    @staticmethod
    def verify(token: str) -> bool:
        return token == SERVICE_ROLE_KEY

    def authenticate(self):
        header = request.headers.get("Authorization")
        if not header or not header.startswith("Bearer "):
            raise APIException("Unauthorized", 401)
        else:
            token = header.split(" ")[1]
            if not token or not self.verify(token):
                raise APIException("Unauthorized", 401)


def require_authentication(func):
    def wrapper(*args, **kwargs):
        AuthMiddleware().authenticate()
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__

    return wrapper
