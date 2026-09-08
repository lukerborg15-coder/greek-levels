import os
from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable '{name}' is not set. Check your .env file.")
    return value


TASTYTRADE_CLIENT_SECRET = _require_env("TASTYTRADE_CLIENT_SECRET")
TASTYTRADE_REFRESH_TOKEN = _require_env("TASTYTRADE_REFRESH_TOKEN")

# Symbols
SPX_SYMBOL = "SPX"       # for ES bias
NDX_SYMBOL = "QQQ"       # for NQ bias (QQQ tracks NDX, has free market data on Tastytrade)

# Contract multiplier for index options
CONTRACT_MULTIPLIER = 100

# GEX levels to output (top N positive and negative)
TOP_N_LEVELS = 5

# Filter chain to strikes within +/- this fraction of spot (e.g. 0.15 = +/-15%).
# Percentage-based so the same value works for SPX (~7400) and QQQ (~600).
STRIKE_RANGE_PCT = 0.15

# Display scale factor per symbol — multiplies strike prices and spot price in
# the output ONLY. Useful if you want to translate one symbol's strikes into
# another scale (e.g. QQQ → NDX). Empty by default; raw strikes are shown.
DISPLAY_SCALE: dict[str, float] = {"QQQ": 41.11}  # QQQ → NDX/NQ scale. Update ratio periodically.

# Zone width to display next to each level (e.g. "7,400.00 ±5.00"). Each level
# is really a zone — give it some give when planning entries / stops.
# Rough trader rules of thumb:
#   SPX:  ±5 points
#   NDX:  ±25 points
#   QQQ:  ±0.50
# For symbols not listed, falls back to LEVEL_ZONE_DEFAULT_PCT of strike price.
LEVEL_ZONES: dict[str, float] = {
    "SPX": 2.5,
    "NDX": 10.0,
    "QQQ": 0.25,
}
LEVEL_ZONE_DEFAULT_PCT = 0.0004  # ~0.04% of strike for unknown symbols

# How long (seconds) to collect streaming greeks/summary events before stopping
STREAM_COLLECT_SECONDS = 15.0

# Output path for JSON (optional)
OUTPUT_JSON_PATH = os.environ.get("GREEK_OUTPUT_PATH", "greek_flow/output/levels.json")
