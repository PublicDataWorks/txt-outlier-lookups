import json
import os
import time

import requests
from dotenv import load_dotenv
from loguru import logger

from configs.cache_template import get_template_content_by_name
from constants.urls import (
    CONVERSATION_MESSAGES_URL,
    CREATE_MESSAGE_URL,
    CREATE_POST_URL,
)

load_dotenv(override=True)


class MissiveAPI:
    def __init__(self):
        self.email = os.environ.get("EMAIL")
        self.phone_number = os.environ.get("PHONE_NUMBER")
        self.MISSIVE_SECRET = get_template_content_by_name("missive_secret")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.MISSIVE_SECRET}",
        }
        self.organization = os.environ.get("MISSIVE_ORGANIZATION")

    def get_conversation_messages(self, conversation_id):
        try:
            start_timestamp = int(time.time()) - 7 * 24 * 60 * 60
            url = CONVERSATION_MESSAGES_URL.format(
                conversation_id=conversation_id, until=start_timestamp
            )
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # Raise exception if not a 2xx response
            return response.json()

        except requests.exceptions.RequestException:
            logger.error(
                f"MissiveAPI get conversations failed with status code {response.status_code}: {response.text}\n"
            )
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

    def send_sms_sync(
        self,
        message,
        to_phone,
        conversation_id=None,
        add_label_list=None,
        remove_label_list=None,
    ):
        if add_label_list is None:
            add_label_list = []
        if remove_label_list is None:
            remove_label_list = []
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

            response = requests.post(
                CREATE_MESSAGE_URL, headers=self.headers, data=json.dumps(body)
            )
            response.raise_for_status()  # Raise exception if not a 2xx response
            return response

        except requests.exceptions.RequestException:
            logger.error(
                f"Missive send message failed with status code {response.status_code}: {response.text}\n{body}"
            )
            return None

    def send_post_sync(self, markdowns, conversation_id):
        attachments = [
            {"markdown": markdown, "color": "good"} for markdown in markdowns
        ]
        body = {
            "posts": {
                "conversation": conversation_id,
                "organization": self.organization,
                "notification": {"title": "Weekly Report", "body": "Summary"},
                "username": "TXT Outlier",
                "username_icon": "https://s3.amazonaws.com/missive-assets/missive-avatar.png",
                "attachments": attachments,
            },
        }

        response = requests.post(
            CREATE_POST_URL, headers=self.headers, data=json.dumps(body)
        )
        if not response.ok:
            logger.error(
                f"Create Missive post failed with status code {response.status_code}: {response.text}\n{body}"
            )
            return None

        return response
