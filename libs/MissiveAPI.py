import json
import os
import time

import aiohttp
import requests
from dotenv import load_dotenv

from constants.urls import CONVERSATION_MESSAGES_URL, CREATE_MESSAGE_URL

load_dotenv()


class MissiveAPI:
    def __init__(self):
        self.email = os.environ.get("EMAIL")
        self.phone_number = os.environ.get("PHONE_NUMBER")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('MISSIVE_SECRET')}",
        }
        self.organization = os.environ.get("MISSIVE_ORGANIZATION")

    async def send_sms(
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
                    "body": str(message),
                    "from_field": {"phone_number": self.phone_number},
                    "organization": self.organization,
                    "to_fields": [{"phone_number": to_phone}],
                    "add_shared_labels": add_label_list,
                    "remove_shared_labels": remove_label_list,
                    "send": True,  # Send right away
                },
            }

            if conversation_id is not None:
                body["drafts"]["conversation"] = conversation_id

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    CREATE_MESSAGE_URL,
                    headers=self.headers,
                    data=json.dumps(body),
                ) as response:
                    return await response.text()
            # response = requests.post(
            #     CREATE_MESSAGE_URL, headers=self.headers, data=json.dumps(body)
            # )
            # response.raise_for_status()  # Raise exception if not a 2xx response
            # return response

        except requests.exceptions.RequestException as e:
            return None

    def get_conversation_messages(self, conversation_id):
        try:
            start_timestamp = int(time.time()) - 7 * 24 * 60 * 60
            url = CONVERSATION_MESSAGES_URL.format(
                conversation_id=conversation_id, until=start_timestamp
            )
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # Raise exception if not a 2xx response
            return response.json()

        except requests.exceptions.RequestException as e:
            return None

    def extract_preview_content(self, conversation_id):
        conversation_messages = self.get_conversation_messages(conversation_id)
        if conversation_messages is not None:
            previews = [
                message["preview"]
                for message in conversation_messages["messages"]
                if "preview" in message
            ]
            return previews
        return None
