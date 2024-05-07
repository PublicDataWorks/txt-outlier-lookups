def map_keys_to_result(data):
    if (
        "result" not in data
        or "col_keys" not in data
        or not data["result"]
        or not data["col_keys"]
    ):
        return {}

    result_object = dict(zip(data["col_keys"], data["result"][0]))

    return result_object
