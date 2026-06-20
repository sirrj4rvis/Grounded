import requests

def test_get_fonts_file_returns_font_asset_for_valid_woff2_filename():
    base_url = "http://127.0.0.1:8000"
    valid_font_filename = "example-font.woff2"  # use a representative valid woff2 filename that is expected to exist
    url = f"{base_url}/fonts/{valid_font_filename}"
    headers = {
        "Accept": "font/woff2,application/font-woff2,*/*;q=0.8"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        assert False, f"Request to {url} failed with exception: {e}"

    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
    content_type = response.headers.get("Content-Type", "")
    assert content_type == "font/woff2", f"Expected Content-Type 'font/woff2' but got '{content_type}'"
    assert response.content and len(response.content) > 0, "Response body is empty, expected font asset content"

test_get_fonts_file_returns_font_asset_for_valid_woff2_filename()