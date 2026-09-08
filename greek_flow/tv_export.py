"""Print TradingView paste blobs from greek_flow/output/levels.json.

Run AFTER pipeline.py. Outputs two single-line strings — one for ES, one for NQ —
that paste straight into the matching text-area input in the Pine indicator.
"""

import json
import os
import sys


def _fmt_gex(value: float) -> str:
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000:.1f}B"
    if abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.1f}M"
    if abs_val >= 1_000:
        return f"{sign}{abs_val / 1_000:.0f}K"
    return f"{sign}{abs_val:.0f}"


def _strikes(levels: list[dict]) -> str:
    return ",".join(f"{lvl['strike']:.2f}" for lvl in levels)


def _gexes(levels: list[dict]) -> str:
    return ",".join(_fmt_gex(lvl["gex"]) for lvl in levels)


def _clean_note(note: str) -> str:
    # Drop the leading "Negative vanna flow — " prefix; keep just the reason.
    if " — " in note:
        return note.split(" — ", 1)[1]
    if " - " in note:
        return note.split(" - ", 1)[1]
    return note


def build_blob(data: dict) -> str:
    flip_val = data.get("gex_flip_point")
    flip_str = f"{flip_val:.2f}" if flip_val is not None else ""
    parts = [
        f"spot={data['spot_price']:.2f}",
        f"regime={data['regime']}",
        f"bias={data['daily_bias']}",
        f"conv={data['conviction']}",
        f"flip={flip_str}",
        f"dex={data['aggregate_dex']:.0f}",
        f"dexbias={data['dex_bias']}",
        f"vanna={data['vanna_flow']}",
        f"vnote={_clean_note(data['vanna_note'])}",
        f"R={_strikes(data['resistance_levels'])}",
        f"Rgex={_gexes(data['resistance_levels'])}",
        f"S={_strikes(data['support_levels'])}",
        f"Sgex={_gexes(data['support_levels'])}",
        f"N={_strikes(data['negative_gex_zones'])}",
        f"Ngex={_gexes(data['negative_gex_zones'])}",
    ]
    return ";".join(parts)


def main() -> int:
    path = os.environ.get("GREEK_OUTPUT_PATH", "greek_flow/output/levels.json")
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. Run pipeline.py first.", file=sys.stderr)
        return 1

    with open(path, "r", encoding="utf-8") as f:
        levels = json.load(f)

    spx = levels.get("SPX")
    qqq = levels.get("QQQ")

    print("=" * 70)
    print("ES BLOB (paste into 'ES paste blob' field in indicator):")
    print("=" * 70)
    if spx:
        print(build_blob(spx))
    else:
        print("(no SPX data)")
    print()
    print("=" * 70)
    print("NQ BLOB (paste into 'NQ paste blob' field in indicator):")
    print("=" * 70)
    if qqq:
        print(build_blob(qqq))
    else:
        print("(no QQQ data)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
