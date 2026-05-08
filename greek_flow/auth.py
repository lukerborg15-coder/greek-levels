import requests

BASE_URL = "https://api.tastytrade.com"


def get_session_token(username: str, password: str) -> str:
    """Authenticate and return session token. Raise on failure."""
    url = f"{BASE_URL}/sessions"
    payload = {"login": username, "password": password}
    response = requests.post(url, json=payload)
    if not response.ok:
        raise RuntimeError(
            f"Tastytrade authentication failed: HTTP {response.status_code} — {response.text}"
        )
    data = response.json()
    token = data.get("data", {}).get("session-token")
    if not token:
        raise RuntimeError(f"Tastytrade authentication response missing session-token: {data}")
    return token
