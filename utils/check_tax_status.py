from utils.map_keys_to_result import map_keys_to_result


def check_tax_status(response):
    owner_data = map_keys_to_result(response.metadata)
    if "tax_status" in owner_data:
        if owner_data["tax_status"] == "OK":
            return "NO_TAX_DEBT"
        else:
            return "TAX_DEBT"
    return "NO_INFORMATION"
