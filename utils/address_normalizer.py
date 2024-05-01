import re

from scourgify import NormalizeAddress


def check_address_format(address):
    # Regex pattern to capture three parts of the address
    pattern = r"^(\d+)\s([\w\s-]+)(\s(St|Rd|Ave|Blvd|Drive|Lane|Road|Way|Court|Circle|Terrace|Place|Square|Loop|Trail|Parkway|Alley|Avenue|Boulevard|Street|Park))?$"

    # Perform regex search with re.IGNORECASE flag for case-insensitive matching
    return re.search(pattern, address, re.IGNORECASE)


def get_first_valid_normalized_address(address_list):
    # Check if the address list is empty
    if not address_list:
        return None

    # Iterate over each address in the list
    for address in address_list:
        # Check if the first character of the address is a digit and if the address contains a space
        if address and address[0].isdigit() and " " in address:
            try:
                # Try to normalize the address
                normalized_address = NormalizeAddress(address).normalize()

                # If normalization is successful, return the normalized address
                return normalized_address
            except Exception:
                # If normalization fails, ignore the exception and continue to the next address
                continue

    # If no valid address is found, return None
    return None
