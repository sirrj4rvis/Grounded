import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 180  # seconds for /ask endpoint as per instructions
ASK_ENDPOINT = f"{BASE_URL}/ask"
HEADERS = {"Content-Type": "application/json"}

def test_post_ask_validates_input_parameters_and_returns_422_on_invalid_input():
    test_cases = [
        # Missing query
        ({}, "missing query"),
        # Empty query
        ({"query": ""}, "empty query"),
        # Query length over 2000 characters
        ({"query": "a" * 2001}, "query length over 2000"),
        # top_k less than 1
        ({"query": "What is AI?", "top_k": 0}, "top_k less than 1"),
        # top_k greater than 10
        ({"query": "What is AI?", "top_k": 11}, "top_k greater than 10"),
        # mode unsupported value
        ({"query": "What is AI?", "mode": "unsupported_mode"}, "unsupported mode"),
        # Combined invalid: query missing and invalid top_k
        ({"top_k": -1}, "missing query and invalid top_k"),
        # Combined invalid: query too long and unsupported mode
        ({"query": "a" * 3000, "mode": "invalid"}, "query too long and unsupported mode")
    ]

    for payload, scenario in test_cases:
        try:
            response = requests.post(
                ASK_ENDPOINT,
                json=payload,
                headers=HEADERS,
                timeout=TIMEOUT
            )
        except requests.RequestException as e:
            assert False, f"Request failed for scenario '{scenario}': {e}"

        assert response.status_code == 422, (
            f"Expected HTTP 422 for scenario '{scenario}', got {response.status_code} with response: {response.text}"
        )

test_post_ask_validates_input_parameters_and_returns_422_on_invalid_input()