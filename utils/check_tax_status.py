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
                if "tax_due" in owner_data:
                    if owner_data["tax_due"] > 0:
                        tax_status = "TAX_DEBT"
                        pass
                tax_status = None
                pass

    return tax_status, rental_status
