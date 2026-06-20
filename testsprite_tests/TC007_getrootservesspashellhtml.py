import requests

def test_get_root_serves_spa_shell_html():
    url = "http://127.0.0.1:8000/"
    headers = {
        "Accept": "text/html"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        assert response.status_code == 200
        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type.lower()
        html_content = response.text
        # Basic sanity checks on SPA shell html content
        assert "<html" in html_content.lower()
        assert "<body" in html_content.lower()
        assert "<div" in html_content.lower()  # React apps typically root in div
    except requests.RequestException as e:
        assert False, f"Request to / failed: {e}"

test_get_root_serves_spa_shell_html()