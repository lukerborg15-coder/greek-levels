import sys
import requests
from datetime import date

from config import BASE_URL


def fetch_chain(symbol: str, session_token: str) -> list:
    """
    Fetch full options chain for symbol.
    Returns a flat list of option records, each containing:
      - strike_price (float)
      - option_type ("C" or "P")
      - expiration_date (str)
      - open_interest (int)
      - delta (float)
      - gamma (float)
      - vanna (float)
    Raise RuntimeError on API failure.
    """
    headers = {"Authorization": session_token}
    resp = requests.get(
        f"{BASE_URL}/option-chains/{symbol}/nested",
        headers=headers,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Chain fetch failed for {symbol}: HTTP {resp.status_code} — {resp.text}"
        )

    data = resp.json()
    # Tastytrade nested chain: data -> data -> items[] -> expirations[]
    items = data.get("data", {}).get("items", [])
    if not items:
        raise RuntimeError(f"No option chain data returned for {symbol}")

    # Collect all expirations across all chain roots
    all_expirations = []
    for item in items:
        all_expirations.extend(item.get("expirations", []))

    today = date.today()

    # Front-month: nearest expiration with at least 1 day to expiry
    valid_expirations = [
        exp for exp in all_expirations
        if (date.fromisoformat(exp["expiration-date"]) - today).days >= 1
    ]

    if not valid_expirations:
        raise RuntimeError(
            f"No valid front-month expiration found for {symbol} — all expirations expire today or in the past"
        )

    front_month = min(valid_expirations, key=lambda e: e["expiration-date"])
    exp_date = front_month["expiration-date"]
    strikes = front_month.get("strikes", [])

    records = []
    for strike_entry in strikes:
        strike_price = float(strike_entry.get("strike-price", 0))

        for opt_type, key in [("C", "call"), ("P", "put")]:
            opt_data = strike_entry.get(key, {}) or {}
            if not opt_data:
                continue

            # Greeks may be nested under "greeks" key or at the top level
            greeks = opt_data.get("greeks") or {}
            oi = opt_data.get("open-interest") or greeks.get("open-interest")
            delta = greeks.get("delta")
            gamma = greeks.get("gamma")
            vanna = greeks.get("vanna")

            if any(v is None for v in [oi, delta, gamma, vanna]):
                print(
                    f"WARNING: Missing greeks for {symbol} {opt_type} strike={strike_price} exp={exp_date} — skipping",
                    file=sys.stderr,
                )
                continue

            records.append({
                "strike_price": strike_price,
                "option_type": opt_type,
                "expiration_date": exp_date,
                "open_interest": int(oi),
                "delta": float(delta),
                "gamma": float(gamma),
                "vanna": float(vanna),
            })

    return records
