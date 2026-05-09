import os
from dotenv import load_dotenv

load_dotenv()

TASTYTRADE_USERNAME = os.environ["TASTYTRADE_USERNAME"]
TASTYTRADE_PASSWORD = os.environ["TASTYTRADE_PASSWORD"]

BASE_URL = "https://api.tastytrade.com"

SPX_SYMBOL = "SPX"
NDX_SYMBOL = "NDX"

CONTRACT_MULTIPLIER = 100
TOP_N_LEVELS = 5
OUTPUT_JSON_PATH = os.environ.get("GREEK_OUTPUT_PATH", "output/levels.json")
