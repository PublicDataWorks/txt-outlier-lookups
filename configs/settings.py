import os

key = os.environ.get("OPENAI_API_KEY")


def get_address_parser_prompt(addresses):
    return (
        "You are given a list of potential addresses along with their timestamps. For each address:\n"
        "1. Normalize it using USPS standards (capitalizing letters, standardizing directionals, and suffixes).\n"
        "2. Identify the main address (e.g., street number, directional, street name, suffix) as 'address'.\n"
        "3. Identify any unit/apartment/suite number as 'sunit'.\n"
        "4. Prefer the newest valid address (based on datetime) when multiple valid addresses exist.\n"
        "5. Once you identify the best valid address, stop processing.\n\n"
        f"Here is the list of potential addresses with timestamps:\n{addresses}\n\n"
        "Return exactly one JSON object in the format:\n"
        "{\n"
        " 'address': '[MAIN ADDRESS]',\n"
        " 'sunit': '[UNIT OR EMPTY STRING]'\n"
        "}\n\n"
        "If you cannot parse ANY address from the list, return:\n"
        "{\n"
        " 'address': null,\n"
        " 'sunit': null\n"
        "}"
    )
