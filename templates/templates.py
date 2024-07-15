templates = {
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
        "you. Text another address if you want to look up another. Text MENU to see our other info. If you're "
        "all set you can just text ALL GOOD."
    ),
    "match_second_message": (
        "If this doesn’t look right or you have any questions text REPORTER and we’ll follow up with you "
        "within 48 hours. Or if you want tips and extra info about tax debt or rules for rentals type MORE."
    ),
    "land_bank": (
        "If this doesn’t look right or you have any questions text REPORTER and we’ll follow up with you "
        "within 48 hours. Or if you want more info about the land bank text LANDBANK."
    ),
    "tax_unconfirmed": (
        "An “unconfirmed“ tax status is used when the Wayne County Treasurer's office thinks the total "
        "amount of tax due might change. This could be because a payment was made very recently, "
        "or a check bounced, for example. If your tax status is unconfirmed, you can call the Treasurer's "
        "office at 313-224-5990, or you can text REPORTER if you have more questions."
    ),
    "sms_history_summary": (
        f"""
        Given the following SMS messages history, generate a summary of major themes and topics discussed:

        Provide the summary in the following format:
        - **User Satisfaction**: ...
        - **Problem Addressed**: ...
        - **Crisis Averted**: ...
        - **Property Status Inquiries**: ...
        - **Accountability Initiatives**: ...
        """
    ),
    "search_prompt": (
        """Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
        You can order the results by a relevant column to return the most interesting examples in the database.
        Never query for all the columns from a specific table, only ask for a few relevant columns given the question.
        ALWAYS FOLLOW THE GIVEN BELOW RULES.
        Pay attention to use only the column names that you can see in the schema description.
        Be careful to not query for columns that do not exist.
        Pay attention to which column is in which table.
        Also, qualify column names with the table name when needed.
        You are required to use the following format, each taking one line:
        Address will follow the format of a number followed by a street name.
        If the properties is not a rental then omit that from the result.
        If rental_status value is 'IS NOT' then must hide rental status from the result.
        Avoid showing anything about rental status like 'It is not registered as a residential rental property'.
        SQLQuery: SQL Query to run
        SQLResult: Result of the SQLQuery
        Only use tables listed below. {schema}
        Question: {query_str}"""
    ),
    "search_context": (
        """The mi_wayne_detroit table gives information regarding the properties and owners of a given city where owner is the name of the owner as OWNER NAME AND tax_due is the tax debt amount
        tax_status is the tax status of the place and rental status is the rental status.
        The table residential_rental_registrations contains list of all rental properties in mi_wayne_detroit.
        Write a query follow exactly this format, DO NOT change anything except for the query value
        SELECT mi_wayne_detroit.owner, CASE WHEN residential_rental_registrations.lat IS NOT NULL THEN 'IS' ELSE 'IS NOT' END AS rental_status, mi_wayne_detroit.tax_due,
        mi_wayne_detroit.tax_status FROM mi_wayne_detroit LEFT JOIN residential_rental_registrations ON ST_DWithin( mi_wayne_detroit.wkb_geometry,
        residential_rental_registrations.wkb_geometry , 0.001) and strict_word_similarity(upper(mi_wayne_detroit.saddstr), upper(residential_rental_registrations.street_name)) > 0.8 WHERE mi_wayne_detroit.address ILIKE 'address%'
        If rental_status value is 'IS NOT' then must hide rental status from the result
        Avoid showing anything about rental status like 'It is not registered as a residential rental property' or 'The property is not registered as a residential rental.' or similar.
        Always return mi_wayne_detroit.owner, mi_wayne_detroit.tax debt and mi_wayne_detroit.tax
        Address will follow the format of a number followed by a street name and street suffix.
        Do not use keywords like 'yes' or 'more' as query value."""
    ),
    "search_context_with_sunit": (
        """The mi_wayne_detroit table gives information regarding the properties and owners of a given city where owner is the name of the owner as OWNER NAME AND tax_due is the tax debt amount
        tax_status is the tax status of the place and rental status is the rental status.
        The table residential_rental_registrations contains list of all rental properties in mi_wayne_detroit.
        Write a query follow exactly this format, DO NOT change anything except for the query value
        SELECT mi_wayne_detroit.owner, CASE WHEN residential_rental_registrations.lat IS NOT NULL THEN 'IS' ELSE 'IS NOT' END AS rental_status, mi_wayne_detroit.tax_due, 
        mi_wayne_detroit.tax_status FROM mi_wayne_detroit LEFT JOIN residential_rental_registrations ON ST_DWithin( mi_wayne_detroit.wkb_geometry, 
        residential_rental_registrations.wkb_geometry , 0.001) and strict_word_similarity(upper(mi_wayne_detroit.saddstr), upper(residential_rental_registrations.street_name)) > 0.8 WHERE mi_wayne_detroit.address ILIKE 'address%' AND mi_wayne_detroit.sunit ILIKE '%sunit'
        If rental_status value is 'IS NOT' then must hide rental status from the result.
        Avoid showing anything about rental status like 'It is not registered as a residential rental property' or 'The property is not registered as a residential rental.' or similar.
        Always return mi_wayne_detroit.owner, mi_wayne_detroit.tax debt and mi_wayne_detroit.tax
        Address will follow the format of a number followed by a street name and street suffix.
        Do not use keywords like 'yes' or 'more' as query value"""
    ),
    "text_summary_prompt": (
        f"""
        Given the following list of messages history, generate a short summary of major themes and topics discussed:
        """
    ),
    "search_model": "gpt-3.5-turbo",
    "summary_model": "gpt-4o",
    "comments_title": "Reporter notes",
    "outcome_title": "Impact and outcomes",
    "messages_title": "Communication patterns",
}
