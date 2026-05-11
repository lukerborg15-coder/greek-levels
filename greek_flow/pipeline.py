import asyncio
import sys

from greek_flow import config
from greek_flow.auth import create_session
from greek_flow.chain import fetch_chain_with_greeks, get_spot_price
from greek_flow.greeks import calculate_gex, calculate_dex, calculate_vanna
from greek_flow.output import build_level_map, print_level_map, save_level_map


def _scale_level_map(level_map: dict, scale: float) -> dict:
    """Multiply strike-price fields by scale; leave GEX/DEX values untouched."""
    scaled = dict(level_map)
    scaled["spot_price"] = level_map["spot_price"] * scale
    if level_map["gex_flip_point"] is not None:
        scaled["gex_flip_point"] = level_map["gex_flip_point"] * scale
    for key in ("resistance_levels", "support_levels", "negative_gex_zones"):
        scaled[key] = [{"strike": lvl["strike"] * scale, "gex": lvl["gex"]} for lvl in level_map[key]]
    return scaled


async def _run_async(symbols: list[str]) -> None:
    print("Authenticating with Tastytrade (OAuth2)...", file=sys.stderr)
    session = create_session(config.TASTYTRADE_CLIENT_SECRET, config.TASTYTRADE_REFRESH_TOKEN)

    all_level_maps = {}

    for symbol in symbols:
        print(f"\nProcessing {symbol}...", file=sys.stderr)
        try:
            print(f"  Fetching spot price for {symbol}...", file=sys.stderr)
            spot_price = await get_spot_price(session, symbol)
            print(f"  Spot price: {spot_price:.2f}", file=sys.stderr)

            chain = await fetch_chain_with_greeks(
                session,
                symbol,
                spot_price,
                strike_range=spot_price * config.STRIKE_RANGE_PCT,
                collect_seconds=config.STREAM_COLLECT_SECONDS,
            )

            gex = calculate_gex(chain, spot_price, config.CONTRACT_MULTIPLIER)
            dex = calculate_dex(chain, config.CONTRACT_MULTIPLIER)
            vanna = calculate_vanna(chain, config.CONTRACT_MULTIPLIER)

            level_map = build_level_map(gex, dex, vanna, spot_price, config.TOP_N_LEVELS)

            # Apply display scale (e.g. QQQ strikes -> NQ-equivalent prices)
            scale = config.DISPLAY_SCALE.get(symbol.upper(), 1.0)
            if scale != 1.0:
                level_map = _scale_level_map(level_map, scale)

            # Attach the per-symbol level zone width so output can display "±X"
            zone = config.LEVEL_ZONES.get(symbol.upper())
            if zone is None:
                zone = spot_price * config.LEVEL_ZONE_DEFAULT_PCT
            level_map["level_zone"] = zone * scale  # match the scaled prices

            print()
            print_level_map(symbol, level_map)

            all_level_maps[symbol] = level_map
        except Exception as exc:
            print(
                f"  ! Failed to process {symbol}: {exc}\n"
                f"    (skipping {symbol}; may need a different data subscription or symbol format)",
                file=sys.stderr,
            )

    save_level_map(all_level_maps, config.OUTPUT_JSON_PATH)
    print(f"\nLevel maps saved to {config.OUTPUT_JSON_PATH}", file=sys.stderr)


def run(symbols: list[str] | None = None) -> None:
    """Full pipeline: authenticate, fetch chains and live greeks, build level maps."""
    if symbols is None:
        symbols = [config.SPX_SYMBOL, config.NDX_SYMBOL]
    asyncio.run(_run_async(symbols))


if __name__ == "__main__":
    run()
