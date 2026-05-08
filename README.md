# Greek Levels

Standalone greek flow pipeline for ES/NQ daily bias and level generation.

Separate from the Topstep backtesting pipeline. Do not mix these codebases.

## What goes here

- `greek_flow/` — the Python module built from GEX_PIPELINE_BUILDER_PROMPT.md
- `requirements_greek.txt` — dependencies for this module only
- `.env` — your Tastytrade credentials (never commit this)
- `output/` — JSON level files generated each morning

## Setup

1. Create a `.env` file with your Tastytrade credentials
2. Install dependencies: `pip install -r requirements_greek.txt`
3. Run: `python greek_flow/pipeline.py`
