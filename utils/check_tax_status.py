from utils.map_keys_to_result import map_keys_to_result


def check_tax_status(response):
    print(response)
    owner_data = map_keys_to_result(response.metadata)
    if "tax_status" in owner_data:
        match owner_data["tax_status"]:
            case "OK":
                return "NO_TAX_DEBT"
            case "FORFEITED":
                return "FORFEITED"
            case "FORECLOSED":
                return "FORECLOSED"
            case _:
                return "NO_INFORMATION"
    return "NO_INFORMATION"
