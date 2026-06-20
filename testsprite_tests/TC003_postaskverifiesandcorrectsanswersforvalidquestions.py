import requests
import time

def test_post_ask_verifies_and_corrects_answers_for_valid_questions():
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/ask"
    headers = {"Content-Type": "application/json"}

    # Valid payload with optional parameters top_k and mode
    payload = {
        "query": "What is photosynthesis?",
        "top_k": 3,
        "mode": "regenerate"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=180)
    except requests.exceptions.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected HTTP 200 but got {response.status_code}"
    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    # Validate top-level keys
    expected_keys = {"query", "answer", "corrected", "groundedness", "abstained", "threshold", "iterations", "claims", "sources", "note"}
    assert expected_keys.issubset(data.keys()), f"Response JSON missing keys: {expected_keys - data.keys()}"

    # Validate types and constraints
    assert isinstance(data["query"], str) and 1 <= len(data["query"]) <= 2000
    assert isinstance(data["answer"], str) and len(data["answer"]) > 0
    assert isinstance(data["corrected"], str) and len(data["corrected"]) >= 0
    assert isinstance(data["groundedness"], float) and 0.0 <= data["groundedness"] <= 1.0
    assert isinstance(data["abstained"], bool)
    assert isinstance(data["threshold"], float)
    assert isinstance(data["iterations"], int) and data["iterations"] >= 0
    assert isinstance(data["claims"], list)
    assert isinstance(data["sources"], list)
    assert isinstance(data["note"], str)

    # Validate claims array content
    for claim in data["claims"]:
        assert isinstance(claim, dict), "Each claim should be a dict"
        claim_keys = {"text", "support", "supported", "evidence"}
        assert claim_keys.issubset(claim.keys()), f"Claim missing keys: {claim_keys - claim.keys()}"
        assert isinstance(claim["text"], str)
        assert isinstance(claim["support"], float) and 0.0 <= claim["support"] <= 1.0
        assert isinstance(claim["supported"], bool)
        # evidence may be a list or similar, but check existence and type
        assert isinstance(claim["evidence"], (list, tuple))

    # Validate sources array content
    for source in data["sources"]:
        assert isinstance(source, dict), "Each source should be a dict"
        source_keys = {"id", "source"}
        assert source_keys.issubset(source.keys()), f"Source missing keys: {source_keys - source.keys()}"
        assert isinstance(source["id"], (int, str))
        assert isinstance(source["source"], str)

test_post_ask_verifies_and_corrects_answers_for_valid_questions()