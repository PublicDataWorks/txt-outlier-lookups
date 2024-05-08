import hashlib
import hmac
import json
import os
from unittest.mock import Mock, patch

from middlewares.auth_middleware import AuthMiddleware
from utils.address_normalizer import (
    check_address_format,
)
from utils.check_property_status import check_property_status
from utils.map_keys_to_result import map_keys_to_result


def test_map_keys_to_result_with_proper_data():
    data = {
        "result": [[1, "John", "Doe"]],
        "col_keys": ["id", "first_name", "last_name"],
    }
    expected = {"id": 1, "first_name": "John", "last_name": "Doe"}
    assert map_keys_to_result(data) == expected


def test_map_keys_to_result_with_missing_result():
    data = {"col_keys": ["id", "first_name", "last_name"]}
    expected = {}
    assert map_keys_to_result(data) == expected


def test_map_keys_to_result_with_missing_keys():
    data = {
        "result": [[1, "John", "Doe"]],
    }
    expected = {}
    assert map_keys_to_result(data) == expected


def test_map_keys_to_result_with_empty_result():
    data = {"result": [], "col_keys": ["id", "first_name", "last_name"]}
    expected = {}
    assert map_keys_to_result(data) == expected
    expected = {}
    assert map_keys_to_result(data) == expected


def test_check_property_status_registered_no_tax_debt():
    response = Mock()
    response.metadata = {
        "result": [["John Doe", "IS", "OK", 0]],
        "col_keys": ["owner_name", "rental_status", "tax_status", "tax_due"],
    }
    tax_status, rental_status = check_property_status(response)
    assert tax_status == "NO_TAX_DEBT"
    assert rental_status == "REGISTERED"


def test_check_property_status_unregistered_forfeited():
    response = Mock()
    response.metadata = {
        "result": [["John Doe", "IS NOT", "FORFEITED", 0]],
        "col_keys": ["owner_name", "rental_status", "tax_status", "tax_due"],
    }
    tax_status, rental_status = check_property_status(response)
    assert tax_status == "FORFEITED"
    assert rental_status == "UNREGISTERED"


def test_check_property_status_registered_tax_debt():
    response = Mock()
    response.metadata = {
        "result": [["John Doe", "IS", "UNKNOWN", 100]],
        "col_keys": ["owner_name", "rental_status", "tax_status", "tax_due"],
    }
    tax_status, rental_status = check_property_status(response)
    assert tax_status == "TAX_DEBT"
    assert rental_status == "REGISTERED"


def test_check_property_status_unknown_no_tax_debt():
    response = Mock()
    response.metadata = {
        "result": [["John Doe", "IS NOT", "OK", 100]],
        "col_keys": ["owner_name", "rental_status", "tax_status", "tax_due"],
    }
    tax_status, rental_status = check_property_status(response)
    assert tax_status == "NO_TAX_DEBT"
    assert rental_status == "UNREGISTERED"


def create_hash(secret, request_body):
    data = json.dumps(request_body).encode()
    hmac_obj = hmac.new(secret.encode(), data, digestmod=hashlib.sha256)
    return hmac_obj.hexdigest()


@patch("os.getenv", return_value="my_secret")
def test_verify_method(mock_getenv):
    secret = "my_secret"  # replace with actual secret
    request_body = {
        "rule": {
            "id": "47251afd-6f29-45e1-96a7-77f5e4eb461c",
            "description": "z. Lookup. CHECK NUMBER FOR ADDRESS",
            "type": "incoming_twilio_message",
        },
        "conversation": {
            "id": "410ca243-af1e-475e-9a20-a86502d9ad2e",
            "created_at": 1707452590,
            "subject": None,
            "latest_message_subject": "SMS with +1 (330) 679-5612",
            "organization": {
                "id": "7deec8a7-439a-414c-a10a-059142216786",
                "name": "Outlier Staging",
            },
            "color": None,
            "authors": [
                {"name": "+1 (330) 679-5612", "phone_number": "+13306795612"},
                {"name": "TXT OUTLIER", "phone_number": "+18336856203"},
                {"name": "TXT OUTLIER"},
            ],
            "external_authors": [
                {"name": "+1 (330) 679-5612", "phone_number": "+13306795612"},
                {"name": "TXT OUTLIER"},
            ],
            "messages_count": 209,
            "drafts_count": 10,
            "send_later_messages_count": 0,
            "attachments_count": 0,
            "tasks_count": 0,
            "completed_tasks_count": 0,
            "users": [
                {
                    "id": "241d4e76-6c0c-42e1-9f32-9621452faf47",
                    "name": "Kate Abbey-Lambertz",
                    "email": "kate@outliermedia.org",
                    "unassigned": False,
                    "closed": False,
                    "archived": False,
                    "trashed": False,
                    "junked": False,
                    "assigned": True,
                    "flagged": False,
                    "snoozed": False,
                },
                {
                    "id": "2d98b928-c3be-4cc6-8087-0baa2235e86e",
                    "name": "Rajiv Sinclair",
                    "email": "rajiv@publicdata.works",
                    "unassigned": False,
                    "closed": False,
                    "archived": True,
                    "trashed": False,
                    "junked": False,
                    "assigned": False,
                    "flagged": False,
                    "snoozed": False,
                },
                {
                    "id": "4fe21e14-c584-45f9-b6e9-c0eaeec41462",
                    "name": "Sarah Alvarez",
                    "email": "sarah@outliermedia.org",
                    "unassigned": False,
                    "closed": False,
                    "archived": False,
                    "trashed": False,
                    "junked": False,
                    "assigned": True,
                    "flagged": False,
                    "snoozed": False,
                },
                {
                    "id": "6335aa04-e15b-4e23-ad0e-e41cdc1295a5",
                    "name": "Dat Tran",
                    "email": "dat.h.tran@stanyangroup.com",
                    "unassigned": False,
                    "closed": False,
                    "archived": True,
                    "trashed": False,
                    "junked": False,
                    "assigned": False,
                    "flagged": False,
                    "snoozed": False,
                },
                {
                    "id": "815e18a9-eab9-4b89-8227-de6518f5d987",
                    "name": "Ky Phan",
                    "email": "ky.phan@stanyangroup.com",
                    "unassigned": False,
                    "closed": False,
                    "archived": True,
                    "trashed": False,
                    "junked": False,
                    "assigned": False,
                    "flagged": False,
                    "snoozed": False,
                },
                {
                    "id": "cd89f926-901a-4d36-83eb-4f7e8881118d",
                    "name": "Sukari Stone",
                    "email": "sukari@publicdata.works",
                    "unassigned": False,
                    "closed": False,
                    "archived": True,
                    "trashed": False,
                    "junked": False,
                    "assigned": False,
                    "flagged": False,
                    "snoozed": False,
                },
            ],
            "assignees": [
                {
                    "id": "241d4e76-6c0c-42e1-9f32-9621452faf47",
                    "name": "Kate Abbey-Lambertz",
                    "email": "kate@outliermedia.org",
                    "unassigned": False,
                    "closed": False,
                    "archived": False,
                    "trashed": False,
                    "junked": False,
                    "assigned": True,
                    "flagged": False,
                    "snoozed": False,
                },
                {
                    "id": "4fe21e14-c584-45f9-b6e9-c0eaeec41462",
                    "name": "Sarah Alvarez",
                    "email": "sarah@outliermedia.org",
                    "unassigned": False,
                    "closed": False,
                    "archived": False,
                    "trashed": False,
                    "junked": False,
                    "assigned": True,
                    "flagged": False,
                    "snoozed": False,
                },
            ],
            "assignee_names": "Kate Abbey-Lambertz, Sarah Alvarez",
            "assignee_emails": "kate@outliermedia.org, sarah@outliermedia.org",
            "shared_label_names": "Else message received",
            "web_url": "https://mail.missiveapp.com/#inbox/conversations/410ca243-af1e-475e-9a20-a86502d9ad2e",
            "app_url": "missive://mail.missiveapp.com/#inbox/conversations/410ca243-af1e-475e-9a20-a86502d9ad2e",
            "team": {
                "id": "48cae1dd-c5cf-45ea-a4ca-73064784ad14",
                "name": "Newsroom",
                "organization": "7deec8a7-439a-414c-a10a-059142216786",
            },
            "shared_labels": [
                {
                    "id": "0cf16332-2d8f-424b-af6e-07d62399cfc3",
                    "name": "Else message received",
                    "name_with_parent_names": "Temporary labels/Else message received",
                    "organization": "7deec8a7-439a-414c-a10a-059142216786",
                    "color": None,
                    "parent": "33d51912-1562-4334-b993-5ba27c47a265",
                    "share_with_organization": False,
                    "share_with_users": [],
                    "share_with_team": None,
                    "visibility": "organization",
                }
            ],
        },
        "message": {
            "id": "565b1709-c750-4650-aaa8-13149e7d0521",
            "preview": "30740 GERALDINE ST",
            "type": "sms",
            "delivered_at": 1713867781,
            "updated_at": 1713867781,
            "created_at": 1713867781,
            "references": ["+13306795612+18336856203"],
            "from_field": {
                "id": "+18336856203",
                "name": "+1 (330) 679-5612",
                "username": None,
            },
            "to_fields": [{"id": "+13306795612", "name": "TXT OUTLIER", "username": None}],
            "external_id": "SM46442ca28915953bbc11ce8bc58fb7b3",
            "account_author": {
                "id": "+13306795612",
                "name": "+1 (330) 679-5612",
                "username": None,
            },
            "account_recipients": [
                {"id": "+18336856203", "name": "TXT OUTLIER", "username": None}
            ],
            "attachments": [],
            "author": None,
        },
    }  # replace with actual request body
    correct_hash = create_hash(secret, request_body)
    os.environ["HMAC_SECRET"] = secret
    result = AuthMiddleware.verify(correct_hash, request_body)
    assert result


class TestCheckAddressFormat:
    def test_correct_format(self):
        assert check_address_format("123 Main St") == "123 Main St"
        assert check_address_format("456 Broadway AVE") == "456 Broadway AVE"
        assert check_address_format("789 Park Lane") == "789 Park Lane"
        assert check_address_format("1000 Market Blvd") == "1000 Market Blvd"

    def test_incorrect_format(self):
        assert check_address_format("123") is None
        assert check_address_format("Broadway Avenue") is None
        assert check_address_format("18936 Littlefield St, Detroit, MI 48235") is None
