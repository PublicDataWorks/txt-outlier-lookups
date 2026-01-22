import os

key = os.environ.get("OPENAI_API_KEY")


def get_address_parser_prompt(addresses):
    return (
        "You are given a list of potential addresses along with their timestamps. For each address:\n"
        "1. Normalize it using USPS standards (capitalizing letters, standardizing directionals, and suffixes).\n"
        "2. Identify the main address (e.g., street number, directional, street name, suffix) as 'address'.\n"
        "3. Identify any unit/apartment/suite number as 'sunit'.\n"
        "4. Prefer the newest valid address (based on datetime) when multiple valid addresses exist.\n"
        "5. IMPORTANT: Strip any city, state, and zip code from the address. All addresses in this system are "
        "for Detroit, MI, so do NOT include 'Detroit', 'MI', 'Michigan', or zip codes (like 48228) in the output. "
        "Only return the street address and unit information. "
        "For example, '8956 Mansfield Detroit, MI 48228' should become "
        "'8956 MANSFIELD ST'. However, preserve 'Detroit' or 'Michigan' if they are part of a street name "
        "(e.g., '17130 Detroit St' → '17130 DETROIT ST', '1234 Michigan Ave' → '1234 MICHIGAN AVE'). "
        "Still extract and return any unit/apartment information in 'sunit' when present "
        "(e.g., '8829 Quincy St #1, Detroit, MI 48204' should yield 'address': '8829 QUINCY ST', 'sunit': '#1').\n"
        "6. Once you have identified and normalized the best valid address, stop processing.\n\n"
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
