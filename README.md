# Greek Levels

Options gamma exposure (GEX) pipeline for ES/NQ daily bias and level generation.

Streams live option chains and greeks from Tastytrade, aggregates gamma exposure across strikes to identify dealer positioning, and exports the resulting price levels as JSON and TradingView Pine Script.

---

## What it does

**1. Pulls the chain.** Authenticates to Tastytrade over OAuth2 and fetches the nested option chain (strikes, expirations, symbols) via the REST API.

**2. Streams live greeks.** The REST API returns chain *structure* only — greeks and open interest come from the DXLink streaming feed:

- `Greeks` event → delta, gamma, theta, rho, vega, implied volatility
- `Summary` event → open interest
- `Quote` event → bid/ask

**3. Computes vanna.** Vanna isn't provided by the feed, so it's derived from Black-Scholes using the IV and time-to-expiry from the Greeks event, with a configurable risk-free rate and per-symbol dividend yields.

**4. Aggregates gamma exposure.** For each strike:

```
GEX = gamma × open_interest × contract_multiplier × spot_price
```

Calls and puts are netted per strike, then summed to get aggregate GEX. The sign of the aggregate determines the **gamma regime**:

- **Positive gamma** — dealers are long gamma and hedge against price movement, which tends to dampen volatility
- **Negative gamma** — dealers are short gamma and hedge with the move, which tends to amplify volatility

**5. Finds the flip point.** Walking strikes in ascending order and accumulating GEX, the **flip point** is the strike where cumulative exposure crosses zero — the boundary between the two regimes.

**6. Exports levels.** Writes daily levels to JSON and generates a TradingView Pine Script overlay, with a configurable ± zone width per symbol.

---

## Setup

```bash
pip install -r requirements_greek.txt
```

Create a `.env` in the project root:

```
TASTYTRADE_CLIENT_SECRET=your_client_secret
TASTYTRADE_REFRESH_TOKEN=your_refresh_token
```

`.env` is gitignored and has never been committed. Credentials are read via environment variables only — there are no secrets anywhere in this repository or its history.

## Run

```bash
python greek_flow/pipeline.py
```

Output lands in `greek_flow/output/` as JSON, plus a `.pine` file for TradingView.

---

## Layout

```
greek_flow/
├── auth.py       OAuth2 session creation
├── chain.py      Chain fetch + DXLink greeks/OI streaming + vanna
├── config.py     Symbols, strike ranges, zone widths, env loading
├── greeks.py     GEX aggregation, regime detection, flip point
├── output.py     JSON level export
├── pipeline.py   Entry point
└── tv_export.py  Pine Script generation
```

`greek_levels.pine` in the repo root is **generated output**, not hand-written source — it's a committed sample of what `tv_export.py` produces, checked in so you can see the result without running the pipeline. It gets overwritten on each run.

## Configuration

Per-symbol settings live in `config.py`: strike range as a percentage of spot, zone width, contract multiplier, and dividend yield. Symbol failures are non-fatal — missing data on one symbol won't kill the run.

## How this was built

This project was built with AI assistance, and the two prompt files in the repo root are the record of that:

- **`GEX_PIPELINE_BUILDER_PROMPT.md`** — the spec I wrote to generate the first implementation: data sources, the GEX math, the auth flow, module boundaries, and a checklist of what "done" meant.
- **`GEX_PIPELINE_AUDITOR_PROMPT.md`** — an adversarial review pass run against the result, checking for hardcoded credentials, wrong API method names, sign errors in the gamma aggregation, and spec drift.

They're committed deliberately rather than deleted. The interesting part of the work is the specification and the audit — knowing what GEX is, how dealer hedging flows actually work, which parts of the output are assumptions, and what an auditor should go looking for. The prompts show that reasoning; the code is what fell out of it.

Everything here has been read, run against live data, and corrected by hand where the generated version was wrong — the commit history has the fixes (async method names, vanna derivation, per-symbol failure handling).

## Notes

- Defaults to QQQ over NDX for free data access; strike ranges are percentage-based so they adapt across symbols
- Risk-free rate and dividend yields are assumptions used only for vanna; vanna is fairly insensitive to them and the directional sign matters more than exact magnitude
- Not investment advice. This generates levels for discretionary reference, not trade signals.
