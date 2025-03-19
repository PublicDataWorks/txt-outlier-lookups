import re

from scourgify import NormalizeAddress

from libs.MissiveAPI import MissiveAPI

missive_client = MissiveAPI()


def check_address_format(address):
    # Regex pattern to capture three parts of the address
    pattern = (r"^(\d+)\s([\w\s-]+)(\s(St|Rd|Ave|Blvd|Drive|Lane|Road|Way|Court|Circle|Terrace|Place|Square|Loop|Trail"
               r"|Parkway|Alley|Avenue|Boulevard|Street|Park))?$")

    # Perform regex search with re.IGNORECASE flag for case-insensitive matching
    if re.search(pattern, address, re.IGNORECASE):
        return address
    else:
        return None
