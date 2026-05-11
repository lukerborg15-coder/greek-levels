import os
import requests

BASE_URL = os.environ.get("TASTYTRADE_BASE_URL", "https://api.tastytrade.com")


def get_access_token(client_secret: str, refresh_token: str) -> str:
    """Exchange a Tastytrade OAuth2 refresh token for an access token. Raise on failure.

    Access tokens are short-lived (~15 minutes), but that's plenty for one
    pipeline run. The refresh token never expires.
    """
    url = f"{BASE_URL}/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    response = requests.post(url, json=payload, timeout=10)
    if not response.ok:
        raise RuntimeError(
            f"Tastytrade OAuth token exchange failed: HTTP {response.status_code} — {response.text}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Tastytrade OAuth returned non-JSON body: {response.text}"
        ) from exc
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Tastytrade OAuth response missing access_token: {data}")
    return token
