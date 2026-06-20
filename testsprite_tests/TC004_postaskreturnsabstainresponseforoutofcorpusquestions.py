import requests

def test_post_ask_returns_abstain_response_for_out_of_corpus_question():
    base_url = "http://127.0.0.1:8000"
    endpoint = "/ask"
    url = base_url + endpoint
    headers = {"Content-Type": "application/json"}

    payload = {
        "query": "Who won the 2026 IPL final?"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=180)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    assert isinstance(data, dict), "Response JSON is not a dictionary"

    assert data.get("abstained") is True, "Expected 'abstained' field to be True for out-of-corpus question"

    refusal_messages = [
        "I can't answer this from the provided context.",
        "I can't answer this from the provided context"
    ]
    note = data.get("note", "")
    # The refusal message may appear in 'note' or in 'answer' or 'corrected' fields
    refusal_found = any(refusal_msg in note for refusal_msg in refusal_messages)
    if not refusal_found:
        # check answer and corrected fields
        answer = data.get("answer", "")
        corrected = data.get("corrected", "")
        refusal_found = any(refusal_msg in answer for refusal_msg in refusal_messages) or \
                        any(refusal_msg in corrected for refusal_msg in refusal_messages)

    assert refusal_found, (
        "Expected refusal message indicating inability to answer from the provided context not found in response"
    )

test_post_ask_returns_abstain_response_for_out_of_corpus_question()