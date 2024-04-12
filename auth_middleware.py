import os
import hmac
import hashlib
import json

from flask import request

from exceptions import APIException


class AuthMiddleware:

    @staticmethod
    def verify(hash: str, request_body: dict) -> bool:
        secret = os.getenv("HMAC_SECRET")
        if secret is None:
            raise ValueError("HMAC_SECRET must be set.")

        data = json.dumps(request_body).encode()

        key_prefix = 'sha256='
        cleaned_header_sig = hash[len(key_prefix):] if hash.startswith(key_prefix) else hash
        decoded_signature = bytes.fromhex(cleaned_header_sig)

        hmac_obj = hmac.new(secret.encode(), data, digestmod=hashlib.sha256)
        generated_signature = hmac_obj.digest()

        return hmac.compare_digest(decoded_signature, generated_signature)

    def authenticate(self):
        hash = request.headers.get("X-Hook-Signature")

        if not hash:
            raise APIException("Unauthorized", 401)

        if not self.verify(hash, request.json):
            raise APIException("Unauthorized", 401)

def require_authentication(func):
    def wrapper(*args, **kwargs):
        AuthMiddleware().authenticate()
        return func(*args, **kwargs)

    return wrapper