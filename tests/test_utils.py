from unittest.mock import Mock

from utils.check_tax_status import check_tax_status
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


def test_check_tax_status_no_debt():
    response = Mock()
    response.metadata = {"result": [["FORFEITED"]], "col_keys": ["tax_status"]}
    assert check_tax_status(response) == "FORFEITED"


def test_check_tax_status_with_debt():
    response = Mock()
    response.metadata = {"result": [["FORECLOSED"]], "col_keys": ["tax_status"]}
    assert check_tax_status(response) == "FORECLOSED"


def test_check_tax_status_no_tax_status():
    response = Mock()
    response.metadata = {"result": [["John Doe"]], "col_keys": ["name"]}
    assert check_tax_status(response) == "NO_INFORMATION"
