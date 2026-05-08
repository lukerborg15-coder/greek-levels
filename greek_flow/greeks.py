from collections import defaultdict


def calculate_gex(chain: list[dict], spot_price: float, contract_multiplier: int) -> dict:
    calls_by_strike = defaultdict(float)
    puts_by_strike = defaultdict(float)

    for record in chain:
        strike = record["strike_price"]
        gex = record["gamma"] * record["open_interest"] * contract_multiplier * spot_price
        if record["option_type"] == "C":
            calls_by_strike[strike] += gex
        else:
            puts_by_strike[strike] += gex

    all_strikes = sorted(set(list(calls_by_strike.keys()) + list(puts_by_strike.keys())))
    by_strike = {s: calls_by_strike[s] - puts_by_strike[s] for s in all_strikes}
    aggregate = sum(by_strike.values())
    regime = "positive" if aggregate >= 0 else "negative"

    # GEX flip point: strike where cumulative GEX crosses zero
    flip_point = None
    cumulative = 0.0
    for strike in all_strikes:
        prev = cumulative
        cumulative += by_strike[strike]
        if (prev < 0 <= cumulative) or (prev > 0 >= cumulative):
            flip_point = strike
            break

    return {"by_strike": by_strike, "aggregate": aggregate, "flip_point": flip_point, "regime": regime}


def calculate_dex(chain: list[dict], contract_multiplier: int) -> dict:
    by_strike = defaultdict(float)

    for record in chain:
        strike = record["strike_price"]
        dex = record["delta"] * record["open_interest"] * contract_multiplier
        by_strike[strike] += dex

    by_strike = dict(sorted(by_strike.items()))
    aggregate = sum(by_strike.values())

    total_abs = sum(abs(v) for v in by_strike.values())
    if total_abs == 0 or abs(aggregate) < 0.1 * total_abs:
        bias = "neutral"
    elif aggregate > 0:
        bias = "bullish"
    else:
        bias = "bearish"

    return {"by_strike": by_strike, "aggregate": aggregate, "bias": bias}


def calculate_vanna(chain: list[dict], contract_multiplier: int) -> dict:
    aggregate = 0.0
    total_abs = 0.0

    for record in chain:
        exposure = record["vanna"] * record["open_interest"] * contract_multiplier
        aggregate += exposure
        total_abs += abs(exposure)

    if total_abs == 0 or abs(aggregate) < 0.1 * total_abs:
        flow_direction = "neutral"
        note = "Vanna flow is neutral — IV changes will have limited directional impact"
    elif aggregate > 0:
        flow_direction = "bullish"
        note = "Positive vanna flow — IV compression adds buying pressure"
    else:
        flow_direction = "bearish"
        note = "Negative vanna flow — IV compression adds selling pressure"

    return {"aggregate": aggregate, "flow_direction": flow_direction, "note": note}
