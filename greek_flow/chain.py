import os
import sys
from datetime import date, datetime
import requests

BASE_URL = os.environ.get("TASTYTRADE_BASE_URL", "https://api.tastytrade.com")


def fetch_chain(symbol: str, session_token: str) -> list[dict]:
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
    url = f"{BASE_URL}/option-chains/{symbol}/nested"
    headers = {"Authorization": session_token}
    response = requests.get(url, headers=headers, timeout=15)
    if not response.ok:
        raise RuntimeError(
            f"Failed to fetch chain for {symbol}: HTTP {response.status_code} — {response.text}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Non-JSON response fetching chain for {symbol}: {response.text}") from exc

    items = data.get("data", {}).get("items", [])
    today = date.today()

    # Find front-month: earliest expiration with at least 1 day to expiry
    front_month = None
    for item in sorted(items, key=lambda x: x.get("expiration-date", "")):
        exp_str = item.get("expiration-date", "")
        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if exp_date > today:
            front_month = item
            break

    if front_month is None:
        raise RuntimeError(f"No valid front-month expiration found for {symbol}")

    records = []
    exp_date_str = front_month.get("expiration-date", "")
    for strike in front_month.get("strikes", []):
        try:
            strike_price = float(strike["strike-price"])
        except (KeyError, TypeError, ValueError):
            print(f"Warning: skipping strike row for {symbol} {exp_date_str} — missing strike-price", file=sys.stderr)
            continue
        for opt_type, key in [("C", "call"), ("P", "put")]:
            opt = strike.get(key, {})
            if opt is None:
                continue
            try:
                delta = float(opt["delta"])
                gamma = float(opt["gamma"])
                vanna = float(opt["vanna"])
                oi = int(opt["open-interest"])
            except (KeyError, TypeError, ValueError):
                print(
                    f"Warning: skipping {symbol} {exp_date_str} {strike_price} {opt_type} — missing greeks or open-interest",
                    file=sys.stderr,
                )
                continue
            records.append({
                "strike_price": strike_price,
                "option_type": opt_type,
                "expiration_date": exp_date_str,
                "open_interest": oi,
                "delta": delta,
                "gamma": gamma,
                "vanna": vanna,
            })

    return records
