def check_property_status(rental_status, tax_status, tax_due=None):
    if tax_due is None:
        tax_due = 0

    if rental_status:
        match rental_status:
            case "IS":
                rental_status = "REGISTERED"
            case "IS NOT":
                rental_status = "UNREGISTERED"
            case _:
                return None, None

    if tax_status:
        match tax_status:
            case "OK":
                tax_status = "NO_TAX_DEBT"
            case "FORFEITED":
                tax_status = "FORFEITED"
            case "FORECLOSED":
                tax_status = "FORFEITED"
            case _:
                tax_status = None

    if tax_due > 0 and not tax_status:
        tax_status = "TAX_DEBT"

    return tax_status, rental_status
