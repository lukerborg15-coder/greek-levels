import json
import os


def build_level_map(gex: dict, dex: dict, vanna: dict, spot_price: float, top_n: int) -> dict:
    by_strike = gex["by_strike"]
    regime = gex["regime"]
    gex_flip_point = gex["flip_point"]
    aggregate_dex = dex["aggregate"]
    dex_bias = dex["bias"]
    vanna_flow = vanna["flow_direction"]
    vanna_note = vanna["note"]

    # Daily bias from DEX only
    if dex_bias == "neutral":
        daily_bias = "neutral"
    elif dex_bias == "bullish":
        daily_bias = "long"
    else:
        daily_bias = "short"

    # Conviction from vanna alignment
    if daily_bias == "neutral":
        conviction = "medium"
    elif (daily_bias == "long" and vanna_flow == "bullish") or (daily_bias == "short" and vanna_flow == "bearish"):
        conviction = "high"
    elif vanna_flow == "neutral":
        conviction = "medium"
    else:
        conviction = "low"

    # Level selection
    resistance_levels = sorted(
        [{"strike": s, "gex": v} for s, v in by_strike.items() if s > spot_price and v > 0],
        key=lambda x: x["gex"], reverse=True
    )[:top_n]

    support_levels = sorted(
        [{"strike": s, "gex": v} for s, v in by_strike.items() if s < spot_price and v > 0],
        key=lambda x: x["gex"], reverse=True
    )[:top_n]

    negative_gex_zones = sorted(
        [{"strike": s, "gex": v} for s, v in by_strike.items() if v < 0],
        key=lambda x: abs(x["gex"]), reverse=True
    )[:top_n]

    return {
        "spot_price": spot_price,
        "regime": regime,
        "daily_bias": daily_bias,
        "conviction": conviction,
        "gex_flip_point": gex_flip_point,
        "resistance_levels": resistance_levels,
        "support_levels": support_levels,
        "negative_gex_zones": negative_gex_zones,
        "aggregate_dex": aggregate_dex,
        "dex_bias": dex_bias,
        "vanna_flow": vanna_flow,
        "vanna_note": vanna_note,
    }


def _format_gex(value: float) -> str:
    abs_val = abs(value)
    sign = "+" if value >= 0 else "-"
    if abs_val >= 1_000_000_000:
        return f"{sign}{abs_val / 1_000_000_000:.1f}B"
    elif abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.1f}M"
    else:
        return f"{sign}{abs_val:,.0f}"


def _symbol_suffix(symbol: str) -> str:
    if symbol.upper() == "SPX":
        return "for ES"
    elif symbol.upper() == "NDX":
        return "for NQ"
    return symbol


def print_level_map(symbol: str, level_map: dict) -> None:
    sep = "=" * 50
    print(sep)
    print(f"GREEK FLOW LEVELS — {symbol.upper()} ({_symbol_suffix(symbol)})")
    print(sep)
    print(f"Spot Price:      {level_map['spot_price']:,.2f}")

    regime_label = (
        "POSITIVE GEX (pinning/mean-reverting)"
        if level_map["regime"] == "positive"
        else "NEGATIVE GEX (trending/volatile)"
    )
    print(f"Regime:          {regime_label}")
    print(f"Daily Bias:      {level_map['daily_bias'].upper()}")

    conviction = level_map["conviction"].upper()
    if conviction == "HIGH":
        conviction_str = "HIGH (vanna flow confirms)"
    elif conviction == "MEDIUM":
        conviction_str = "MEDIUM (vanna flow neutral)"
    else:
        conviction_str = "LOW (vanna flow contradicts)"
    print(f"Conviction:      {conviction_str}")
    print()

    flip = level_map["gex_flip_point"]
    flip_str = f"{flip:,.2f}" if flip is not None else "None"
    print(f"GEX Flip Point:  {flip_str}")
    print()

    print("RESISTANCE LEVELS (above spot):")
    if level_map["resistance_levels"]:
        for lvl in level_map["resistance_levels"]:
            print(f"  {lvl['strike']:>9,.2f}  |  GEX: {_format_gex(lvl['gex'])}")
    else:
        print("  None")
    print()

    print("SUPPORT LEVELS (below spot):")
    if level_map["support_levels"]:
        for lvl in level_map["support_levels"]:
            print(f"  {lvl['strike']:>9,.2f}  |  GEX: {_format_gex(lvl['gex'])}")
    else:
        print("  None")
    print()

    print("NEGATIVE GEX ZONES (acceleration zones):")
    if level_map["negative_gex_zones"]:
        for lvl in level_map["negative_gex_zones"]:
            print(f"  {lvl['strike']:>9,.2f}  |  GEX: {_format_gex(lvl['gex'])}")
    else:
        print("  None")
    print()

    dex_sign = "bullish" if level_map["aggregate_dex"] >= 0 else "bearish"
    print(f"DEX Aggregate:   {level_map['aggregate_dex']:>+,.0f} ({dex_sign})")
    vanna_note_short = level_map['vanna_note'].split(' — ')[1] if ' — ' in level_map['vanna_note'] else level_map['vanna_note']
    print(f"Vanna Flow:      {level_map['vanna_flow'].upper()} ({vanna_note_short})")
    print(sep)


def save_level_map(level_map: dict, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(level_map, f, indent=2)
