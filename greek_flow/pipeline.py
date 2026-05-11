import asyncio
import sys

from greek_flow import config
from greek_flow.auth import create_session
from greek_flow.chain import fetch_chain_with_greeks, get_spot_price
from greek_flow.greeks import calculate_gex, calculate_dex, calculate_vanna
from greek_flow.output import build_level_map, print_level_map, save_level_map


async def _run_async(symbols: list[str]) -> None:
    print("Authenticating with Tastytrade (OAuth2)...", file=sys.stderr)
    session = create_session(config.TASTYTRADE_CLIENT_SECRET, config.TASTYTRADE_REFRESH_TOKEN)

    all_level_maps = {}

    for symbol in symbols:
        print(f"\nProcessing {symbol}...", file=sys.stderr)

        print(f"  Fetching spot price for {symbol}...", file=sys.stderr)
        spot_price = await get_spot_price(session, symbol)
        print(f"  Spot price: {spot_price:.2f}", file=sys.stderr)

        chain = await fetch_chain_with_greeks(
            session,
            symbol,
            spot_price,
            strike_range=config.STRIKE_RANGE_POINTS,
            collect_seconds=config.STREAM_COLLECT_SECONDS,
        )

        gex = calculate_gex(chain, spot_price, config.CONTRACT_MULTIPLIER)
        dex = calculate_dex(chain, config.CONTRACT_MULTIPLIER)
        vanna = calculate_vanna(chain, config.CONTRACT_MULTIPLIER)

        level_map = build_level_map(gex, dex, vanna, spot_price, config.TOP_N_LEVELS)
        print()
        print_level_map(symbol, level_map)

        all_level_maps[symbol] = level_map

    save_level_map(all_level_maps, config.OUTPUT_JSON_PATH)
    print(f"\nLevel maps saved to {config.OUTPUT_JSON_PATH}", file=sys.stderr)


def run(symbols: list[str] | None = None) -> None:
    """Full pipeline: authenticate, fetch chains and live greeks, build level maps."""
    if symbols is None:
        symbols = [config.SPX_SYMBOL, config.NDX_SYMBOL]
    asyncio.run(_run_async(symbols))


if __name__ == "__main__":
    run()
