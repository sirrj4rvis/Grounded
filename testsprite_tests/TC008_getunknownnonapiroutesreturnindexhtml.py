import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 30

def test_get_unknown_non_api_routes_return_index_html():
    routes_to_test = [
        "/app",
        "/some-random-route",
        "/another/unknown/path",
        "/app/dashboard",
        "/any/non-api/endpoint"
    ]
    for route in routes_to_test:
        url = f"{BASE_URL}{route}"
        try:
            response = requests.get(url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as e:
            assert False, f"Request to {url} failed with exception: {e}"
        assert response.status_code == 200, f"Expected status 200 for {url} but got {response.status_code}"
        content_type = response.headers.get("Content-Type", "")
        # The index.html should be text/html
        assert "text/html" in content_type, f"Expected 'text/html' content-type for {url} but got {content_type}"
        # The response text should include at least some marker of index.html content (e.g. <html> tag)
        assert "<html" in response.text.lower(), f"Response content for {url} does not contain expected HTML"

test_get_unknown_non_api_routes_return_index_html()