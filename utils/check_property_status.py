def check_property_status(rental_status, tax_status, tax_due):
    if rental_status:
        match rental_status:
            case "IS":
                rental_status = "REGISTERED"
                pass
            case "IS NOT":
                rental_status = "UNREGISTERED"
                pass
            case _:
                return None

    if tax_status:
        match tax_status:
            case "OK":
                tax_status = "NO_TAX_DEBT"
                pass
            case "FORFEITED":
                tax_status = "FORFEITED"
                pass
            case "FORECLOSED":
                tax_status = "FORFEITED"
                pass
            case _:
                tax_status = None
                pass

    if (
            tax_due > 0
        and not tax_status
    ):
        tax_status = "TAX_DEBT"

    return tax_status, rental_status
