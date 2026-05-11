from tastytrade import Session


def create_session(client_secret: str, refresh_token: str) -> Session:
    """Create an authenticated Tastytrade Session using OAuth2 credentials.

    The Session lazily refreshes its short-lived access token on each API
    request using the long-lived refresh_token + client_secret.
    """
    return Session(client_secret, refresh_token)
