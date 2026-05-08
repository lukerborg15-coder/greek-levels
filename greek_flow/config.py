import os
from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable '{name}' is not set. Check your .env file.")
    return value


TASTYTRADE_USERNAME = _require_env("TASTYTRADE_USERNAME")
TASTYTRADE_PASSWORD = _require_env("TASTYTRADE_PASSWORD")

# Symbols
SPX_SYMBOL = "SPX"       # for ES bias
NDX_SYMBOL = "NDX"       # for NQ bias

# Contract multiplier for index options
CONTRACT_MULTIPLIER = 100

# GEX levels to output (top N positive and negative)
TOP_N_LEVELS = 5

# Output path for JSON (optional)
OUTPUT_JSON_PATH = os.environ.get("GREEK_OUTPUT_PATH", "greek_flow/output/levels.json")
