from __future__ import annotations

import argparse
from pathlib import Path

from portfolio_watch.config import load_settings
from portfolio_watch.notifier import create_notifier
from portfolio_watch.portfolio import load_positions
from portfolio_watch.pricing import create_price_provider
from portfolio_watch.watcher import build_snapshots


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitor portfolio prices and alert thresholds.")
    parser.add_argument(
        "--portfolio",
        type=Path,
        help="Path to portfolio CSV. Defaults to PORTFOLIO_FILE or example data.",
    )
    parser.add_argument(
        "--provider",
        choices=["mock", "yfinance"],
        help="Price provider override. Defaults to PRICE_PROVIDER env var (or 'mock').",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send Telegram alerts for triggered positions when Telegram settings are configured.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    portfolio_file = args.portfolio or settings.portfolio_file

    positions = load_positions(portfolio_file)
    provider = create_price_provider(args.provider or settings.price_provider)
    snapshots = build_snapshots(positions, provider)

    print_report(snapshots)

    if args.notify:
        notifier = create_notifier(
            settings.notifier,
            settings.telegram_bot_token,
            settings.telegram_chat_id,
        )
        notifier.send_snapshot_alerts(snapshots)

    return 0


def print_report(snapshots) -> None:
    print("symbol,name,price,change_percent,market_value,unrealized_gain,unrealized_gain_percent,alert")
    for snapshot in snapshots:
        position = snapshot.position
        quote = snapshot.quote
        print(
            ",".join(
                [
                    position.symbol,
                    position.name,
                    f"{quote.price:.2f}",
                    f"{quote.change_percent:.2f}",
                    f"{snapshot.market_value:.2f}",
                    f"{snapshot.unrealized_gain:.2f}",
                    f"{snapshot.unrealized_gain_percent:.2f}",
                    str(snapshot.should_alert).lower(),
                ]
            )
        )
