import sys
import requests

from greek_flow import config
from greek_flow.auth import get_session_token
from greek_flow.chain import fetch_chain
from greek_flow.greeks import calculate_gex, calculate_dex, calculate_vanna
from greek_flow.output import build_level_map, print_level_map, save_level_map

BASE_URL = "https://api.tastytrade.com"


def get_spot_price(symbol: str, session_token: str) -> float:
    """Fetch current spot price for symbol from Tastytrade quote endpoint."""
    url = f"{BASE_URL}/quotes/{symbol}"
    headers = {"Authorization": session_token}
    response = requests.get(url, headers=headers, timeout=10)
    if not response.ok:
        raise RuntimeError(
            f"Failed to fetch quote for {symbol}: HTTP {response.status_code} — {response.text}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Non-JSON response fetching quote for {symbol}: {response.text}") from exc

    quote_data = data.get("data", {})
    last = quote_data.get("last")
    if last is None:
        items = quote_data.get("items", [])
        if items:
            last = items[0].get("last")
    if last is None:
        raise RuntimeError(f"Quote for {symbol} missing 'last' price field in response: {data}")
    return float(last)


def run(symbols: list[str] | None = None) -> None:
    """
    Full pipeline:
    1. Load config
    2. Authenticate
    3. For each symbol: fetch chain, get spot price, calculate greeks, build level map, print output
    4. Save JSON output
    """
    if symbols is None:
        symbols = [config.SPX_SYMBOL, config.NDX_SYMBOL]

    print("Authenticating with Tastytrade...", file=sys.stderr)
    session_token = get_session_token(config.TASTYTRADE_USERNAME, config.TASTYTRADE_PASSWORD)

    all_level_maps = {}

    for symbol in symbols:
        print(f"Processing {symbol}...", file=sys.stderr)

        chain = fetch_chain(symbol, session_token)
        spot_price = get_spot_price(symbol, session_token)

        gex = calculate_gex(chain, spot_price, config.CONTRACT_MULTIPLIER)
        dex = calculate_dex(chain, config.CONTRACT_MULTIPLIER)
        vanna = calculate_vanna(chain, config.CONTRACT_MULTIPLIER)

        level_map = build_level_map(gex, dex, vanna, spot_price, config.TOP_N_LEVELS)
        print_level_map(symbol, level_map)

        all_level_maps[symbol] = level_map

    save_level_map(all_level_maps, config.OUTPUT_JSON_PATH)
    print(f"\nLevel maps saved to {config.OUTPUT_JSON_PATH}", file=sys.stderr)


if __name__ == "__main__":
    run()
