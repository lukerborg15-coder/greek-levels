"""Fetch options chain with live greeks and open interest via the Tastytrade SDK.

The Tastytrade REST API only returns chain structure (strike/expiration/symbols),
not greeks or open interest. Those come from the DXLink streaming feed:
  - Greeks event:  delta, gamma, theta, rho, vega, volatility
  - Summary event: open_interest

Vanna is not provided by the feed — we compute it from Black-Scholes using the
IV and time-to-expiry from the Greeks event.
"""

import asyncio
import math
import sys
from datetime import date
from typing import Optional

from tastytrade import DXLinkStreamer, Session
from tastytrade.dxfeed import Greeks, Quote, Summary
from tastytrade.instruments import NestedOptionChain

# Vanna calculation assumptions. Vanna is fairly insensitive to these values;
# the directional sign matters more than the exact magnitude.
RISK_FREE_RATE = 0.045  # ~current short rate
DIVIDEND_YIELDS = {"SPX": 0.013, "NDX": 0.008}


def _normal_pdf(x: float) -> float:
    return math.exp(-x * x / 2.0) / math.sqrt(2.0 * math.pi)


def _calc_vanna(spot: float, strike: float, t_years: float, sigma: float, q: float, r: float) -> float:
    """Black-Scholes vanna (dDelta/dSigma). Returns 0 on degenerate inputs."""
    if t_years <= 0 or sigma <= 0 or spot <= 0 or strike <= 0:
        return 0.0
    sqrt_t = math.sqrt(t_years)
    d1 = (math.log(spot / strike) + (r - q + 0.5 * sigma * sigma) * t_years) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    return -math.exp(-q * t_years) * _normal_pdf(d1) * d2 / sigma


async def get_spot_price(session: Session, streamer_symbol: str, timeout: float = 10.0) -> float:
    """Fetch current spot price via a Quote event from the DXLink streamer."""
    async with DXLinkStreamer(session) as streamer:
        await streamer.subscribe(Quote, [streamer_symbol])
        try:
            quote = await asyncio.wait_for(streamer.get_event(Quote), timeout=timeout)
        except asyncio.TimeoutError:
            raise RuntimeError(f"Timed out waiting for Quote on {streamer_symbol}")
    bid = float(quote.bid_price) if quote.bid_price is not None else 0.0
    ask = float(quote.ask_price) if quote.ask_price is not None else 0.0
    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0
    return bid or ask


async def fetch_chain_with_greeks(
    session: Session,
    symbol: str,
    spot_price: float,
    strike_range: float,
    collect_seconds: float = 15.0,
) -> list[dict]:
    """Fetch front-month chain for symbol and stream live greeks + open interest.

    Filters strikes to within +/- strike_range points of spot_price to keep the
    subscription set manageable. Returns a flat list of dict records.
    """
    chains = await NestedOptionChain.a_get(session, symbol)
    if not chains:
        raise RuntimeError(f"No option chain returned for {symbol}")
    chain = chains[0]

    today = date.today()
    valid_expirations = [e for e in chain.expirations if e.expiration_date > today]
    if not valid_expirations:
        raise RuntimeError(f"No valid front-month expiration found for {symbol}")
    front = min(valid_expirations, key=lambda e: e.expiration_date)
    t_years = max(front.days_to_expiration, 1) / 365.0
    q = DIVIDEND_YIELDS.get(symbol.upper(), 0.0)

    # Filter strikes to within +/- strike_range of spot
    low = spot_price - strike_range
    high = spot_price + strike_range
    in_range_strikes = [
        s for s in front.strikes if low <= float(s.strike_price) <= high
    ]
    if not in_range_strikes:
        raise RuntimeError(
            f"No strikes for {symbol} within +/-{strike_range} of spot {spot_price}"
        )

    # Build streamer symbol -> (strike, type, exp_date) map
    symbol_map: dict[str, tuple[float, str, str]] = {}
    streamer_symbols: list[str] = []
    exp_str = front.expiration_date.isoformat()
    for strike in in_range_strikes:
        sp = float(strike.strike_price)
        symbol_map[strike.call_streamer_symbol] = (sp, "C", exp_str)
        symbol_map[strike.put_streamer_symbol] = (sp, "P", exp_str)
        streamer_symbols.append(strike.call_streamer_symbol)
        streamer_symbols.append(strike.put_streamer_symbol)

    print(
        f"  Streaming greeks/OI for {len(streamer_symbols)} contracts "
        f"({len(in_range_strikes)} strikes) for {collect_seconds:.0f}s...",
        file=sys.stderr,
    )

    greeks_store: dict[str, Greeks] = {}
    summary_store: dict[str, Summary] = {}

    async def consume_greeks(streamer: DXLinkStreamer) -> None:
        try:
            async for ev in streamer.listen(Greeks):
                greeks_store[ev.event_symbol] = ev
        except asyncio.CancelledError:
            pass

    async def consume_summary(streamer: DXLinkStreamer) -> None:
        try:
            async for ev in streamer.listen(Summary):
                summary_store[ev.event_symbol] = ev
        except asyncio.CancelledError:
            pass

    async with DXLinkStreamer(session) as streamer:
        await streamer.subscribe(Greeks, streamer_symbols)
        await streamer.subscribe(Summary, streamer_symbols)

        greek_task = asyncio.create_task(consume_greeks(streamer))
        summary_task = asyncio.create_task(consume_summary(streamer))
        try:
            await asyncio.sleep(collect_seconds)
        finally:
            greek_task.cancel()
            summary_task.cancel()
            await asyncio.gather(greek_task, summary_task, return_exceptions=True)

    print(
        f"  Got {len(greeks_store)} greeks events and {len(summary_store)} summary events",
        file=sys.stderr,
    )

    records: list[dict] = []
    skipped = 0
    for sym, (strike_price, opt_type, exp_date) in symbol_map.items():
        g = greeks_store.get(sym)
        s = summary_store.get(sym)
        if g is None or s is None:
            skipped += 1
            continue
        if g.delta is None or g.gamma is None or g.volatility is None:
            skipped += 1
            continue
        sigma = float(g.volatility)
        vanna = _calc_vanna(spot_price, strike_price, t_years, sigma, q, RISK_FREE_RATE)
        records.append(
            {
                "strike_price": strike_price,
                "option_type": opt_type,
                "expiration_date": exp_date,
                "open_interest": int(s.open_interest) if s.open_interest else 0,
                "delta": float(g.delta),
                "gamma": float(g.gamma),
                "vanna": vanna,
            }
        )

    if skipped:
        print(f"  Skipped {skipped} contracts with incomplete data", file=sys.stderr)

    if not records:
        raise RuntimeError(
            f"No usable contracts for {symbol}. Got {len(greeks_store)} greeks and "
            f"{len(summary_store)} summaries from {len(streamer_symbols)} subscriptions."
        )

    return records
