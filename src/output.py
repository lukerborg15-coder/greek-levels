import json
import os


def build_level_map(gex: dict, dex: dict, vanna: dict, spot_price: float, top_n: int) -> dict:
    """
    Returns structured level map:
    {
        "spot_price": float,
        "regime": "positive" | "negative",
        "daily_bias": "long" | "short" | "neutral",
        "conviction": "high" | "medium" | "low",
        "gex_flip_point": float | None,
        "resistance_levels": [{"strike": float, "gex": float}, ...],
        "support_levels": [{"strike": float, "gex": float}, ...],
        "negative_gex_zones": [{"strike": float, "gex": float}, ...],
        "aggregate_dex": float,
        "dex_bias": "bullish" | "bearish" | "neutral",
        "vanna_flow": "bullish" | "bearish" | "neutral",
        "vanna_note": str
    }
    """
    by_strike = gex["by_strike"]

    # Resistance: positive GEX strikes above spot, sorted ascending (nearest first)
    resistance = sorted(
        [{"strike": s, "gex": v} for s, v in by_strike.items() if s > spot_price and v > 0],
        key=lambda x: x["strike"],
    )[:top_n]

    # Support: positive GEX strikes below spot, sorted descending (nearest first)
    support = sorted(
        [{"strike": s, "gex": v} for s, v in by_strike.items() if s < spot_price and v > 0],
        key=lambda x: x["strike"],
        reverse=True,
    )[:top_n]

    # Negative GEX zones: top N by magnitude (most negative first)
    neg_zones = sorted(
        [{"strike": s, "gex": v} for s, v in by_strike.items() if v < 0],
        key=lambda x: x["gex"],
    )[:top_n]

    # Daily bias: follow DEX direction regardless of GEX regime
    if dex["bias"] == "neutral":
        daily_bias = "neutral"
    elif dex["bias"] == "bullish":
        daily_bias = "long"
    else:
        daily_bias = "short"

    # Conviction: vanna alignment with daily bias
    vanna_flow = vanna["flow_direction"]
    if daily_bias == "neutral":
        conviction = "low"
    elif (daily_bias == "long" and vanna_flow == "bullish") or \
         (daily_bias == "short" and vanna_flow == "bearish"):
        conviction = "high"
    elif vanna_flow == "neutral":
        conviction = "medium"
    else:
        conviction = "low"

    return {
        "spot_price": spot_price,
        "regime": gex["regime"],
        "daily_bias": daily_bias,
        "conviction": conviction,
        "gex_flip_point": gex["flip_point"],
        "resistance_levels": resistance,
        "support_levels": support,
        "negative_gex_zones": neg_zones,
        "aggregate_dex": dex["aggregate"],
        "dex_bias": dex["bias"],
        "vanna_flow": vanna_flow,
        "vanna_note": vanna["note"],
    }


def print_level_map(symbol: str, level_map: dict) -> None:
    """Print clean formatted level output to console."""
    sep = "=" * 50

    regime_str = (
        "POSITIVE GEX (pinning/mean-reverting)"
        if level_map["regime"] == "positive"
        else "NEGATIVE GEX (trending/volatile)"
    )

    bias_str = level_map["daily_bias"].upper()

    conviction = level_map["conviction"].upper()
    vanna_flow = level_map["vanna_flow"]
    if level_map["conviction"] == "high":
        conviction_label = f"{conviction} (vanna flow confirms)"
    elif level_map["conviction"] == "medium":
        conviction_label = f"{conviction} (vanna neutral)"
    else:
        conviction_label = f"{conviction} (vanna contradicts)"

    flip = level_map["gex_flip_point"]
    flip_str = f"{flip:.2f}" if flip is not None else "None"

    print(sep)
    print(f"GREEK FLOW LEVELS — {symbol}")
    print(sep)
    print(f"Spot Price:      {level_map['spot_price']:.2f}")
    print(f"Regime:          {regime_str}")
    print(f"Daily Bias:      {bias_str}")
    print(f"Conviction:      {conviction_label}")
    print()
    print(f"GEX Flip Point:  {flip_str}")
    print()

    if level_map["resistance_levels"]:
        print("RESISTANCE LEVELS (above spot):")
        for lvl in level_map["resistance_levels"]:
            gex_b = lvl["gex"] / 1e9
            print(f"  {lvl['strike']:.2f}  |  GEX: +{gex_b:.1f}B")
    else:
        print("RESISTANCE LEVELS (above spot): None")
    print()

    if level_map["support_levels"]:
        print("SUPPORT LEVELS (below spot):")
        for lvl in level_map["support_levels"]:
            gex_b = lvl["gex"] / 1e9
            print(f"  {lvl['strike']:.2f}  |  GEX: +{gex_b:.1f}B")
    else:
        print("SUPPORT LEVELS (below spot): None")
    print()

    if level_map["negative_gex_zones"]:
        print("NEGATIVE GEX ZONES (acceleration zones):")
        for lvl in level_map["negative_gex_zones"]:
            gex_b = lvl["gex"] / 1e9
            print(f"  {lvl['strike']:.2f}  |  GEX: {gex_b:.1f}B")
    else:
        print("NEGATIVE GEX ZONES (acceleration zones): None")
    print()

    dex_val = level_map["aggregate_dex"]
    dex_bias = level_map["dex_bias"]
    print(f"DEX Aggregate:   {dex_val:,.0f} ({dex_bias})")
    print(f"Vanna Flow:      {vanna_flow.upper()} ({level_map['vanna_note']})")
    print(sep)


def save_level_map(level_maps: dict, path: str) -> None:
    """Save level maps as JSON to path."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(level_maps, f, indent=2)
