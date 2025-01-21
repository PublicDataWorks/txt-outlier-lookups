# tests/test_utils.py
from utils.address_normalizer import check_address_format
from utils.check_property_status import check_property_status
from utils.map_keys_to_result import map_keys_to_result


class TestMapKeysToResult:
    def test_with_proper_data(self):
        data = {
            "result": [[1, "John", "Doe"]],
            "col_keys": ["id", "first_name", "last_name"],
        }
        expected = {"id": 1, "first_name": "John", "last_name": "Doe"}
        assert map_keys_to_result(data) == expected

    def test_with_missing_result(self):
        data = {"col_keys": ["id", "first_name", "last_name"]}
        expected = {}
        assert map_keys_to_result(data) == expected

    def test_with_missing_keys(self):
        data = {
            "result": [[1, "John", "Doe"]],
        }
        expected = {}
        assert map_keys_to_result(data) == expected

    def test_with_empty_result(self):
        data = {"result": [], "col_keys": ["id", "first_name", "last_name"]}
        expected = {}
        assert map_keys_to_result(data) == expected


class TestCheckPropertyStatus:
    def test_registered_no_tax_debt(self):
        tax_status, rental_status = check_property_status(rental_status="IS", tax_status="OK", tax_due=0)
        assert tax_status == "NO_TAX_DEBT"
        assert rental_status == "REGISTERED"

    def test_unregistered_forfeited(self):
        tax_status, rental_status = check_property_status(rental_status="IS NOT", tax_status="FORFEITED", tax_due=0)
        assert tax_status == "FORFEITED"
        assert rental_status == "UNREGISTERED"

    def test_registered_tax_debt(self):
        tax_status, rental_status = check_property_status("IS", tax_status=None, tax_due=100)
        assert tax_status == "TAX_DEBT"
        assert rental_status == "REGISTERED"

    def test_unknown_no_tax_debt(self):
        tax_status, rental_status = check_property_status(rental_status="IS NOT", tax_status="OK", tax_due=0)
        assert tax_status == "NO_TAX_DEBT"
        assert rental_status == "UNREGISTERED"


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
