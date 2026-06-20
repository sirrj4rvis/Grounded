import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 30

def test_get_examples_returnsprecomputedverificationexamples():
    url = f"{BASE_URL}/examples"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        # Check HTTP status code 200 for success
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        
        # Attempt to parse JSON
        examples = response.json()
        # Assert it is a list/array
        assert isinstance(examples, list), f"Response JSON is not a list, got {type(examples)}"
        assert len(examples) > 0, "Examples list is empty"
        
        # Check structure of at least one example (Verification object)
        example = examples[0]
        # Required keys from PRD: query, answer, corrected, groundedness, abstained, threshold, claims[], sources[], note
        required_keys = {
            "query",
            "answer",
            "corrected",
            "groundedness",
            "abstained",
            "threshold",
            "claims",
            "sources",
            "note"
        }
        missing_keys = required_keys - example.keys()
        assert not missing_keys, f"Missing keys in example: {missing_keys}"
        
        # Validate claims: array of dicts, each with text, support, supported, evidence
        claims = example.get("claims")
        assert isinstance(claims, list), "Claims is not a list"
        assert len(claims) > 0, "Claims list is empty"
        for claim in claims:
            claim_keys = {"text", "support", "supported", "evidence"}
            assert claim_keys <= claim.keys(), f"Missing keys in claim: {claim_keys - claim.keys()}"
        
        # Validate sources: array of dicts with id and source
        sources = example.get("sources")
        assert isinstance(sources, list), "Sources is not a list"
        assert len(sources) > 0, "Sources list is empty"
        for source in sources:
            source_keys = {"id", "source"}
            assert source_keys <= source.keys(), f"Missing keys in source: {source_keys - source.keys()}"

    except requests.exceptions.RequestException as e:
        # Request could fail if examples file or demo data cannot be loaded
        # The PRD says to receive an error response indicating examples could not be returned
        # So we expect a non-200 status and a JSON or text error message in that case
        if e.response is not None:
            r = e.response
            assert r.status_code != 200, "Expected non-200 status when examples cannot be loaded"
            try:
                err_json = r.json()
                assert "error" in err_json or "detail" in err_json, "Error response missing error/detail message"
            except Exception:
                # not JSON, just ensure some error text present
                assert r.text, "Error response empty"
        else:
            # No response - network or server error in accessing /examples
            assert False, f"Request to /examples failed with no response: {str(e)}"

    except AssertionError:
        raise
    except Exception as ex:
        # Any other unexpected errors
        raise AssertionError(f"Unexpected error during test: {ex}")

test_get_examples_returnsprecomputedverificationexamples()