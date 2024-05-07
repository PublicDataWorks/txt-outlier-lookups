sms_templates = {
    "all_good": (
        "Thanks for using TXT Outlier. Come back anytime by texting DETROIT or another word that would tell "
        "us what kind of resources you might need. You can always text REPORTER and we'll follow up with you. "
        "Text UPDATES if you want to see what kind of weekly updates we offer."
    ),
    "no_match": (
        "We don’t have info for {address}. If you’re sure the address is in Detroit and you entered it correctly text "
        "REPORTER. We’ll get back to you and see what’s going on. If you want to try again just enter an address in "
        "this format “1111 E. Jefferson” or “231 Main St.”"
    ),
    "wrong_format": (
        "We can't not recognize your address. If you’re sure the address is in Detroit and you entered it correctly text "
        "REPORTER. We’ll get back to you and see what’s going on. If you want to try again just enter an address in "
        "this format “1111 E. Jefferson” or “231 Main St.”"
    ),
    "closest_match": (
        "This is the address we think is correct: {address}. Type YES if "
        "that's right. If this doesn't look right enter the address again in this format 1111 E. "
        "Jefferson or 231 Main St."
    ),
    "return_info": (
        "The county has OWNER NAME listed as the owner of ADDRESS. It is RENTAL STATUS as a rental "
        "property with the city. This property has TAX DEBT in outstanding taxes according to the Wayne "
        "County Treasurer. It is listed as COMPLIANT/IN FORFEITURE/FORECLOSED by the Treasurer."
    ),
    "return_info2": (
        "If this doesn't look right or you have any questions text REPORTER and we'll follow up with you "
        "within 48 hours. Or if you want tips and extra info about tax debt or rules for rentals type MORE."
    ),
    "has_tax_debt": (
        "If you own your home and have tax debt, the county does have payment plan options, and there are "
        "some other programs to help if you're having trouble paying off the debt. For payment plans with "
        "the Treasurer call 313-224-5990 or visit https://bit.ly/49VZuLe. "
        "If you're renting, you're not responsible for property taxes unless you have a different "
        "agreement with your landlord."
    ),
    "unregistered": (
        "The city requires rentals to be registered and inspected. Here's the city's page on the rules: "
        "https://bit.ly/49VcuRc. Tenants: see steps from Detroit Renter City for enforcing your rights "
        "under the city's rental ordinance and scheduling an inspection: "
        "https://detroitrentercity.wordpress.com/. Landlords: register your property and obtain "
        "certificates of compliance through the city: https://bit.ly/3vounJ8"
    ),
    "registered": (
        "The city requires rentals to be registered and inspected. Here's the city's page on the rules: "
        "https://bit.ly/49VcuRc. If you have concerns about your property txt REPORTER and we'll follow up "
        "with you."
    ),
    "foreclosed": (
        "If your rental or home is in forfeiture or foreclosure there can still be options to stay. You can "
        "call the United Community Housing Coalition at 313-241-7009 to ask about their Make it Home "
        "program."
    ),
    "forfeited": (
        "If your rental or home is in forfeiture or foreclosure there can still be options to stay. You can "
        "call the United Community Housing Coalition at 313-241-7009 to ask about their Make it Home "
        "program."
    ),
    "final": (
        "If you have questions or don't think these resources will work, text REPORTER and we'll follow up with "
        "you. Text another address if you want to look it up another. Text MENU to see our other info. If you're "
        "all set you can just text ALL SET."
    ),
    "match_second_message": (
        "If this doesn’t look right or you have any questions text REPORTER and we’ll follow up  with you within 48 hours. Or if you want tips and extra info about tax debt or rules for rentals type MORE."
    ),
    "not_in_session": (
        "You are not currently in a lookup session, please initiate one before querying for more infomation."
    ),
}


def get_tax_message(tax_status):
    tax_status_mapping = {
        "TAX_DEBT": sms_templates["has_tax_debt"],
        "NO_TAX_DEBT": sms_templates["no_tax_debt"],
        "FORECLOSED": sms_templates["foreclosed"],
        "FORFEITED": sms_templates["forfeited"],
        "NO_INFORMATION": None,
    }

    return tax_status_mapping.get(tax_status, "Invalid tax status")


def get_rental_message(rental_status):
    rental_status_mapping = {
        "REGISTERED": sms_templates["registered"],
        "UNREGISTERED": sms_templates["unregistered"],
        "NO_INFORMATION": None,
    }

    return rental_status_mapping.get(rental_status, "Invalid rental status")
