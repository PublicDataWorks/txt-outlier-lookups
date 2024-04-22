import json
import os

import requests
from dotenv import load_dotenv

from constants.urls import CREATE_MESSAGE_URL, LIST_LABELS_URL

load_dotenv()

import json
import os

import requests


class MissiveAPI:
    def __init__(self):
        self.email = os.environ.get("EMAIL")
        self.phone_number = os.environ.get("PHONE_NUMBER")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('MISSIVE_SECRET')}",
        }
        self.organization = os.environ.get("MISSIVE_ORGANIZATION")

    def send_sms(
        self,
        message,
        to_phone,
        conversation_id=None,
        add_label_list=[],
        remove_label_list=[],
    ):
        try:
            body = {
                "drafts": {
                    "body": message,
                    "from_field": {
                        "phone_number": self.phone_number,
                    },
                    "organization": self.organization,
                    "to_fields": [{"phone_number": to_phone}],
                    "add_shared_labels": add_label_list,
                    "remove_shared_labels": remove_label_list,
                    "send": True,  # Send right away
                },
            }

            if conversation_id is not None:
                body["drafts"]["conversation"] = conversation_id

            response = requests.post(
                CREATE_MESSAGE_URL, headers=self.headers, data=json.dumps(body)
            )
            response.raise_for_status()  # Raise exception if not a 2xx response
            return response

        except requests.exceptions.RequestException as e:
            print(str(e))
            return None
