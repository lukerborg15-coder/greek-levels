import requests
from config import BASE_URL


def get_session_token(username: str, password: str) -> str:
    """Authenticate and return session token. Raise on failure."""
    resp = requests.post(
        f"{BASE_URL}/sessions",
        json={"login": username, "password": password},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Authentication failed: HTTP {resp.status_code} — {resp.text}"
        )
    data = resp.json()
    token = data.get("data", {}).get("session-token")
    if not token:
        raise RuntimeError(f"session-token missing in auth response: {resp.text}")
    return token
