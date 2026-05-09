def calculate_gex(chain: list, spot_price: float, contract_multiplier: int) -> dict:
    """
    Returns:
    {
        "by_strike": {strike: gex_value, ...},
        "aggregate": float,
        "flip_point": float | None,
        "regime": "positive" | "negative"
    }
    """
    by_strike = {}

    for record in chain:
        strike = record["strike_price"]
        gamma = record["gamma"]
        oi = record["open_interest"]
        opt_type = record["option_type"]

        # GEX = gamma * OI * multiplier * spot_price
        # Calls: positive GEX (MMs long gamma)
        # Puts:  negative GEX (MMs short gamma from put selling)
        gex = gamma * oi * contract_multiplier * spot_price
        if opt_type == "P":
            gex = -gex

        by_strike[strike] = by_strike.get(strike, 0.0) + gex

    aggregate = sum(by_strike.values())
    regime = "positive" if aggregate >= 0 else "negative"

    # Flip point: strike where cumulative GEX (sorted ascending by strike) crosses zero
    flip_point = None
    sorted_strikes = sorted(by_strike.keys())
    cumulative = 0.0
    prev_cumulative = 0.0
    for strike in sorted_strikes:
        prev_cumulative = cumulative
        cumulative += by_strike[strike]
        if prev_cumulative < 0 and cumulative >= 0:
            flip_point = strike
            break
        elif prev_cumulative > 0 and cumulative <= 0:
            flip_point = strike
            break

    return {
        "by_strike": by_strike,
        "aggregate": aggregate,
        "flip_point": flip_point,
        "regime": regime,
    }


def calculate_dex(chain: list, contract_multiplier: int) -> dict:
    """
    Returns:
    {
        "by_strike": {strike: dex_value, ...},
        "aggregate": float,
        "bias": "bullish" | "bearish" | "neutral"
    }
    """
    by_strike = {}

    for record in chain:
        strike = record["strike_price"]
        delta = record["delta"]
        oi = record["open_interest"]

        # DEX = delta * OI * multiplier
        # Put delta is already negative in API data — do NOT negate again.
        # Calls: positive DEX (positive delta)
        # Puts:  negative DEX (delta is already negative)
        dex = delta * oi * contract_multiplier
        by_strike[strike] = by_strike.get(strike, 0.0) + dex

    aggregate = sum(by_strike.values())

    # Neutral band: aggregate within 10% of total absolute DEX exposure
    total_abs_dex = sum(abs(v) for v in by_strike.values())
    neutral_threshold = total_abs_dex * 0.10 if total_abs_dex > 0 else 0.0

    if abs(aggregate) <= neutral_threshold:
        bias = "neutral"
    elif aggregate > 0:
        bias = "bullish"
    else:
        bias = "bearish"

    return {
        "by_strike": by_strike,
        "aggregate": aggregate,
        "bias": bias,
    }


def calculate_vanna(chain: list, contract_multiplier: int) -> dict:
    """
    Returns:
    {
        "aggregate": float,
        "flow_direction": "bullish" | "bearish" | "neutral",
        "note": str
    }
    """
    aggregate = 0.0

    for record in chain:
        vanna = record["vanna"]
        oi = record["open_interest"]
        aggregate += vanna * oi * contract_multiplier

    if aggregate > 0:
        flow_direction = "bullish"
        note = "IV compression adds bid pressure"
    elif aggregate < 0:
        flow_direction = "bearish"
        note = "IV expansion adds sell pressure"
    else:
        flow_direction = "neutral"
        note = "no directional vanna flow"

    return {
        "aggregate": aggregate,
        "flow_direction": flow_direction,
        "note": note,
    }
