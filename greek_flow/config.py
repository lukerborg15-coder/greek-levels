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
# the output ONLY. Used to translate QQQ levels into NQ/NDX-equivalent strikes
# so you can map them to your NQ futures chart. GEX values are NOT scaled because
# they represent real dollar gamma exposure on the underlying being traded.
# NDX/QQQ ratio is roughly 41-42; tweak if it drifts.
DISPLAY_SCALE = {
    "QQQ": 41.5,
}

# How long (seconds) to collect streaming greeks/summary events before stopping
STREAM_COLLECT_SECONDS = 15.0

# Output path for JSON (optional)
OUTPUT_JSON_PATH = os.environ.get("GREEK_OUTPUT_PATH", "greek_flow/output/levels.json")
