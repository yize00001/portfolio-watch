from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False


@dataclass(frozen=True)
class Settings:
    portfolio_file: Path
    price_provider: str
    notifier: str
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    check_interval_seconds: int
    market_timezone: str


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        portfolio_file=Path(os.getenv("PORTFOLIO_FILE", "data/portfolio.example.csv")),
        price_provider=os.getenv("PRICE_PROVIDER", "mock"),
        notifier=os.getenv("NOTIFIER", "none"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
        check_interval_seconds=int(os.getenv("CHECK_INTERVAL_SECONDS", "300")),
        market_timezone=os.getenv("MARKET_TIMEZONE", "Asia/Taipei"),
    )
