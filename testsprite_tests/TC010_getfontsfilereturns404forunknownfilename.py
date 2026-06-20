import requests

def test_getfontsfilereturns404forunknownfilename():
    base_url = "http://127.0.0.1:8000"
    unknown_font_file = "thisfontdoesnotexist.woff2"
    url = f"{base_url}/fonts/{unknown_font_file}"
    try:
        response = requests.get(url, timeout=30)
    except requests.RequestException as e:
        assert False, f"Request failed with exception: {e}"
    assert response.status_code != 200, f"Expected non-200 status code for unknown font file but got {response.status_code}"
    assert response.status_code == 404, f"Expected 404 Not Found status code but got {response.status_code}"

test_getfontsfilereturns404forunknownfilename()