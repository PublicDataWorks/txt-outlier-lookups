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

    def send_sms(self, message, to_phone, conversation_id=None, label_list=[]):
        try:
            body = {
                "drafts": {
                    "body": message,
                    "from_field": {
                        "phone_number": self.phone_number,
                    },
                    "organization": "7deec8a7-439a-414c-a10a-059142216786",
                    "to_fields": [{"phone_number": to_phone}],
                    "add_shared_labels": label_list,
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

    def retrieve_label_id_by_name(self, label_name):
        try:
            response = requests.get(LIST_LABELS_URL, headers=self.headers)
            response.raise_for_status()  # Raise exception if not a 2xx response
            labels = response.json()

            for label in labels["shared_labels"]:
                if label["name"] == label_name:
                    return label["id"]
            return None

        except requests.exceptions.RequestException as e:
            print(str(e))
            return None
        except KeyError as e:
            print(f"Missing key in response: {str(e)}")
            return None
