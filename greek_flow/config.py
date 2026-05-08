import os
from dotenv import load_dotenv

load_dotenv()

TASTYTRADE_USERNAME = os.environ["TASTYTRADE_USERNAME"]
TASTYTRADE_PASSWORD = os.environ["TASTYTRADE_PASSWORD"]

# Symbols
SPX_SYMBOL = "SPX"       # for ES bias
NDX_SYMBOL = "NDX"       # for NQ bias

# Contract multiplier for index options
CONTRACT_MULTIPLIER = 100

# GEX levels to output (top N positive and negative)
TOP_N_LEVELS = 5

# Output path for JSON (optional)
OUTPUT_JSON_PATH = os.environ.get("GREEK_OUTPUT_PATH", "greek_flow/output/levels.json")
