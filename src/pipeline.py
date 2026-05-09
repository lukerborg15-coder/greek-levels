import os
import sys

# Ensure src/ is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

from config import (
    TASTYTRADE_USERNAME,
    TASTYTRADE_PASSWORD,
    BASE_URL,
    CONTRACT_MULTIPLIER,
    TOP_N_LEVELS,
    OUTPUT_JSON_PATH,
    SPX_SYMBOL,
    NDX_SYMBOL,
)
from auth import get_session_token
from chain import fetch_chain
from greeks import calculate_gex, calculate_dex, calculate_vanna
from output import build_level_map, print_level_map, save_level_map

SYMBOL_LABELS = {
    "SPX": "SPX (for ES)",
    "NDX": "NDX (for NQ)",
}


def fetch_spot_price(symbol: str, session_token: str) -> float:
    """Fetch current spot price for symbol from Tastytrade quotes endpoint."""
    headers = {"Authorization": session_token}
    resp = requests.get(
        f"{BASE_URL}/quotes/{symbol}",
        headers=headers,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Quote fetch failed for {symbol}: HTTP {resp.status_code} — {resp.text}"
        )
    data = resp.json()
    # Tastytrade quote response: data.data.last or data.data.items[0].last
    quote_data = data.get("data", {})
    last = quote_data.get("last")
    if last is None:
        items = quote_data.get("items", [])
        if items:
            last = items[0].get("last")
    if last is None:
        raise RuntimeError(
            f"Could not extract spot price for {symbol} — 'last' field missing: {resp.text}"
        )
    return float(last)


def run(symbols: list = None) -> None:
    """
    Full pipeline:
    1. Load config
    2. Authenticate
    3. For each symbol: fetch chain, get spot price, calculate greeks, build level map, print output
    4. Save JSON output
    """
    if symbols is None:
        symbols = [SPX_SYMBOL, NDX_SYMBOL]

    session_token = get_session_token(TASTYTRADE_USERNAME, TASTYTRADE_PASSWORD)

    all_level_maps = {}

    for symbol in symbols:
        chain = fetch_chain(symbol, session_token)
        spot_price = fetch_spot_price(symbol, session_token)

        gex = calculate_gex(chain, spot_price, CONTRACT_MULTIPLIER)
        dex = calculate_dex(chain, CONTRACT_MULTIPLIER)
        vanna = calculate_vanna(chain, CONTRACT_MULTIPLIER)

        level_map = build_level_map(gex, dex, vanna, spot_price, TOP_N_LEVELS)

        label = SYMBOL_LABELS.get(symbol, symbol)
        print_level_map(label, level_map)

        all_level_maps[symbol] = level_map

    save_level_map(all_level_maps, OUTPUT_JSON_PATH)


if __name__ == "__main__":
    run()
