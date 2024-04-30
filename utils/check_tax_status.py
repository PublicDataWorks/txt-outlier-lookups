from utils.map_keys_to_result import map_keys_to_result


def check_tax_status(response):
    owner_data = map_keys_to_result(response.metadata)
    rental_status = ""
    tax_status = ""
    if "rental_status" in owner_data:
        match owner_data["rental_status"]:
            case "IS":
                rental_status = "REGISTERED"
                pass
            case "IS NOT":
                rental_status = "UNREGISTERED"
                pass
            case _:
                return None

    if "tax_status" in owner_data:
        match owner_data["tax_status"]:
            case "OK":
                tax_status = "NO_TAX_DEBT"
                pass
            case "FORFEITED", "FORECLOSED":
                tax_status = "FORFEITED"
                pass
            case _:
                tax_status = None
                pass

    if (
        "tax_due" in owner_data
        and owner_data["tax_due"] is not None
        and owner_data["tax_due"] > 0
        and not tax_status
    ):
        tax_status = "TAX_DEBT"

    return tax_status, rental_status
