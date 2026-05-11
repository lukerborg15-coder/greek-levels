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
NDX_SYMBOL = "NDX"       # for NQ bias

# Contract multiplier for index options
CONTRACT_MULTIPLIER = 100

# GEX levels to output (top N positive and negative)
TOP_N_LEVELS = 5

# Filter chain to strikes within +/- N points of spot (keeps streaming load small)
STRIKE_RANGE_POINTS = 1000

# How long (seconds) to collect streaming greeks/summary events before stopping
STREAM_COLLECT_SECONDS = 15.0

# Output path for JSON (optional)
OUTPUT_JSON_PATH = os.environ.get("GREEK_OUTPUT_PATH", "greek_flow/output/levels.json")
