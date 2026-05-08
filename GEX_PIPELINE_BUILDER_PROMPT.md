# Builder Prompt — Greek Flow Data Pipeline (GEX/DEX/Vanna Level Output)

Use this prompt when sending this implementation task to Codex, Cursor, or another coding agent.

---

## Builder Role

You are the BUILDER for this task.

Your job is to complete **one narrowly scoped task** safely. You are not here to make the repo cleaner, redesign the system, expand features, or improve unrelated code.

This is a **standalone new project**, not an extension of the existing Topstep pipeline. Do not touch any existing files in `src/v3/` or anywhere else in the repo.

---

## Task Mode

**PATCH ONLY**

Build the implementation described below. No design expansion. No extra features. No touching existing pipeline code.

Stop after implementation is complete and report exactly what you built.

---

## Cost-Control Rules

- Do not inspect the entire repo.
- Only read files explicitly listed in this task.
- Do not read the same file repeatedly unless necessary.
- Do not include full file contents in your answer.
- Do not continue into another phase without explicit approval.
- Keep the response under **2500 words** unless explicitly asked otherwise.
- Stop after completing PATCH ONLY.
- If more work is needed, report the next recommended prompt instead of continuing.

---

## Project Rules

- This is a **live data pipeline**, not a backtester. There is no train/test/holdout concept here.
- Never use stale or cached chain data for level calculation — always pull fresh at runtime.
- Never hardcode credentials. All secrets must come from environment variables or a `.env` file.
- Never silently swallow API errors. Fail loudly with a clear error message.
- All greek calculations must be mathematically precise — wrong greeks produce wrong levels.
- Output must be deterministic given the same input chain data.
- Do not write to any existing Topstep pipeline files.

---

## Task Risk Level

**HIGH** — live API authentication, financial greek calculations, level output that will be used for real trading decisions.

Do not proceed unless all acceptance criteria below are explicitly met.

---

## What You Are Building

A standalone Python script: `greek_flow/pipeline.py`

This script runs pre-market each morning. It:
1. Authenticates with the Tastytrade API
2. Pulls the full SPX options chain (for ES bias) and NDX options chain (for NQ bias)
3. Calculates GEX, DEX, and Vanna by strike across the full chain
4. Identifies key levels and daily bias
5. Prints a clean structured level output to the console (and optionally saves to JSON)

---

## File Structure to Create

Create the following new files only. Do not touch anything else.

```
greek_flow/
    __init__.py          (empty)
    pipeline.py          (main script — the full build target)
    config.py            (constants and env var loading)
    auth.py              (Tastytrade authentication)
    chain.py             (options chain fetching)
    greeks.py            (GEX, DEX, Vanna calculations)
    output.py            (level map formatting and JSON export)
requirements_greek.txt   (dependencies only for this module)
```

---

## Files Allowed to Read (for context only, do not edit)

- None from the existing pipeline. This is fully standalone.

## Files Allowed to Create

- All files listed under "File Structure to Create" above.

## Files Off Limits

- Everything in `src/v3/`
- `src/v3/strategies.py`
- `src/v3/evaluator.py`
- `src/v3/topstep.py`
- `src/v3/data.py`
- Any existing test files
- Any existing strategy files
- `pyproject.toml`
- `run-cli.cmd`

---

## Implementation Spec

### `config.py`

Load from environment variables (use `python-dotenv` to read a `.env` file):

```python
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
```

---

### `auth.py`

Authenticate with Tastytrade API using their session endpoint.

Base URL: `https://api.tastytrade.com`

Authentication endpoint: `POST /sessions`

Request body:
```json
{
  "login": "<username>",
  "password": "<password>"
}
```

Response contains a `session-token` field. Store this token and pass it as the `Authorization` header on all subsequent requests.

Function signature:
```python
def get_session_token(username: str, password: str) -> str:
    """Authenticate and return session token. Raise on failure."""
```

Raise a clear `RuntimeError` with the HTTP status and response body if authentication fails. Do not swallow the error.

---

### `chain.py`

Fetch the full options chain for a given symbol.

Endpoint: `GET /option-chains/{symbol}/nested`

This returns all expirations and strikes with greeks included (delta, gamma, vanna, open interest).

Function signature:
```python
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
```

Filter to **front-month expiration only** (nearest expiration with at least 1 day to expiry). Do not include weeklies that expire today.

If the greeks fields are missing or None for a given strike, skip that record and log a warning to stderr. Do not crash.

---

### `greeks.py`

Calculate GEX, DEX, and Vanna exposure by strike from the raw chain records.

#### GEX Calculation

For each strike, for each option type:

```
GEX_per_contract = gamma * open_interest * CONTRACT_MULTIPLIER * spot_price
```

- Calls contribute **positive** GEX
- Puts contribute **negative** GEX (puts are short gamma from MM perspective)

Sum calls and puts at each strike:
```
GEX[strike] = GEX_calls[strike] - GEX_puts[strike]
```

Aggregate GEX (sum across all strikes) determines regime:
- Aggregate GEX > 0 → positive gamma regime (pinning, mean-reverting)
- Aggregate GEX < 0 → negative gamma regime (trending, volatile)

GEX flip point = the strike where cumulative GEX crosses zero (sorted by strike ascending).

#### DEX Calculation

For each strike, for each option type:

```
DEX_per_contract = delta * open_interest * CONTRACT_MULTIPLIER
```

- Calls contribute positive DEX
- Puts contribute negative DEX (puts have negative delta)

```
DEX[strike] = DEX_calls[strike] + DEX_puts[strike]
```

Aggregate DEX = sum across all strikes. Negative aggregate DEX = bearish MM positioning. Positive = bullish.

#### Vanna Calculation

For each strike:

```
Vanna_exposure[strike] = vanna * open_interest * CONTRACT_MULTIPLIER
```

Sum calls and puts. Positive aggregate vanna = bullish flow when IV compresses. Negative = bearish flow when IV compresses.

Vanna is a **flow modifier**, not a level. Report aggregate vanna direction only (positive/negative) and magnitude. Do not report vanna by strike in the level output.

#### Function Signatures

```python
def calculate_gex(chain: list[dict], spot_price: float, contract_multiplier: int) -> dict:
    """
    Returns:
    {
        "by_strike": {strike: gex_value, ...},
        "aggregate": float,
        "flip_point": float | None,
        "regime": "positive" | "negative"
    }
    """

def calculate_dex(chain: list[dict], contract_multiplier: int) -> dict:
    """
    Returns:
    {
        "by_strike": {strike: dex_value, ...},
        "aggregate": float,
        "bias": "bullish" | "bearish" | "neutral"
    }
    """

def calculate_vanna(chain: list[dict], contract_multiplier: int) -> dict:
    """
    Returns:
    {
        "aggregate": float,
        "flow_direction": "bullish" | "bearish" | "neutral",
        "note": str   # human readable explanation
    }
    """
```

---

### `output.py`

Build the level map and bias from the greek calculations.

```python
def build_level_map(gex: dict, dex: dict, vanna: dict, spot_price: float, top_n: int) -> dict:
    """
    Returns structured level map:
    {
        "spot_price": float,
        "regime": "positive" | "negative",
        "daily_bias": "long" | "short" | "neutral",
        "conviction": "high" | "medium" | "low",
        "gex_flip_point": float | None,
        "resistance_levels": [{"strike": float, "gex": float}, ...],  # top N positive GEX above spot
        "support_levels": [{"strike": float, "gex": float}, ...],     # top N positive GEX below spot
        "negative_gex_zones": [{"strike": float, "gex": float}, ...], # top N negative GEX strikes
        "aggregate_dex": float,
        "dex_bias": "bullish" | "bearish" | "neutral",
        "vanna_flow": "bullish" | "bearish" | "neutral",
        "vanna_note": str
    }
    """
```

**Daily bias logic:**
- If regime is positive AND dex_bias is bearish → `"short"`, conviction based on vanna alignment
- If regime is positive AND dex_bias is bullish → `"long"`, conviction based on vanna alignment
- If regime is negative AND dex_bias is bearish → `"short"`, conviction based on vanna alignment
- If regime is negative AND dex_bias is bullish → `"long"`, conviction based on vanna alignment
- If dex aggregate is within 10% of zero → `"neutral"`

**Conviction:**
- `"high"` if vanna flow matches daily bias direction
- `"medium"` if vanna flow is neutral
- `"low"` if vanna flow contradicts daily bias direction

```python
def print_level_map(symbol: str, level_map: dict) -> None:
    """Print clean formatted level output to console."""

def save_level_map(level_map: dict, path: str) -> None:
    """Save level map as JSON to path."""
```

Console output format (example):

```
==================================================
GREEK FLOW LEVELS — SPX (for ES)
==================================================
Spot Price:      5247.50
Regime:          POSITIVE GEX (pinning/mean-reverting)
Daily Bias:      SHORT
Conviction:      HIGH (vanna flow confirms)

GEX Flip Point:  5230.00

RESISTANCE LEVELS (above spot):
  5280.00  |  GEX: +2.4B
  5300.00  |  GEX: +1.8B
  5320.00  |  GEX: +1.1B

SUPPORT LEVELS (below spot):
  5220.00  |  GEX: +3.1B
  5200.00  |  GEX: +1.6B
  5180.00  |  GEX: +0.9B

NEGATIVE GEX ZONES (acceleration zones):
  5260.00  |  GEX: -0.8B
  5240.00  |  GEX: -0.5B

DEX Aggregate:   -182,400 (bearish)
Vanna Flow:      BULLISH (IV compression adds bid)
==================================================
```

---

### `pipeline.py`

The main entry point. Runs the full pipeline for both SPX and NDX.

```python
def run(symbols: list[str] = ["SPX", "NDX"]) -> None:
    """
    Full pipeline:
    1. Load config
    2. Authenticate
    3. For each symbol: fetch chain, get spot price, calculate greeks, build level map, print output
    4. Save JSON output
    """
```

Spot price: fetch from Tastytrade quote endpoint `GET /quotes/{symbol}` — use the `last` price field.

Call `run()` when script is executed directly:
```python
if __name__ == "__main__":
    run()
```

---

### `requirements_greek.txt`

```
requests>=2.31.0
python-dotenv>=1.0.0
```

No other dependencies. Do not use pandas, numpy, or scipy for this module — all calculations are pure Python dicts and lists. This keeps the pipeline lightweight and dependency-free.

---

## Acceptance Criteria

Before submitting, verify each of the following:

- [ ] All files created in `greek_flow/` only — no existing files touched
- [ ] Credentials loaded from environment variables only — no hardcoded secrets
- [ ] `auth.py` raises `RuntimeError` on failed authentication with status code and body
- [ ] `chain.py` filters to front-month expiration only (not today's expiry)
- [ ] `chain.py` skips records with missing greeks and logs warning — does not crash
- [ ] GEX: calls positive, puts negative, summed by strike
- [ ] DEX: calls positive delta, puts negative delta, summed by strike
- [ ] Vanna: summed by strike, reported as aggregate flow direction only
- [ ] GEX flip point correctly identifies where cumulative GEX crosses zero
- [ ] Level map correctly separates resistance (positive GEX above spot) from support (positive GEX below spot)
- [ ] Daily bias logic follows the exact 4-regime table in this spec
- [ ] Conviction correctly reflects vanna alignment
- [ ] Console output matches the format shown in this spec
- [ ] JSON output saves correctly to configured path
- [ ] `pipeline.py` runs end to end for both SPX and NDX
- [ ] No imports from `src/v3/` or any existing pipeline module

---

## What to Report When Done

1. Full content of each created file
2. Confirmation of each acceptance criterion above (check or flag)
3. Any deviations from this spec and why (there should be none)
4. Any API behavior you discovered that differed from the spec (e.g. different field names in the response)

Do not run the pipeline live. Do not run tests. Stop here and wait for auditor review.
