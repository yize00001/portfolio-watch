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
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run as a Telegram bot: respond to /status and auto-alert during market hours.",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Import portfolio CSV into SQLite DB (data/portfolio.db) and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    args = build_parser().parse_args(argv)
    settings = load_settings()
    portfolio_file = args.portfolio or settings.portfolio_file
    provider = create_price_provider(args.provider or settings.price_provider)

    if args.migrate:
        from portfolio_watch.database import DB_PATH, add_lot, init_db
        db_path = DB_PATH
        positions = load_positions(portfolio_file)
        init_db(db_path)
        for pos in positions:
            add_lot(
                pos.symbol,
                pos.name,
                pos.quantity,
                pos.average_cost,
                pos.currency,
                db_path=db_path,
            )
        print(f"Migrated {len(positions)} position(s) from {portfolio_file} → {db_path}")
        return 0

    if args.watch:
        from portfolio_watch.bot import PortfolioBot
        from portfolio_watch.notifier import TelegramNotifier
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
            return 1
        bot = PortfolioBot(
            notifier=TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id),
            portfolio_file=portfolio_file,
            price_provider=provider,
            check_interval=settings.check_interval_seconds,
        )
        bot.run()
        return 0

    positions = load_positions(portfolio_file)
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
