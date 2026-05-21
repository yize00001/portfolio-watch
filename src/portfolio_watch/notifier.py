from __future__ import annotations

from abc import ABC, abstractmethod

import requests

from portfolio_watch.models import PositionSnapshot


class Notifier(ABC):
    @abstractmethod
    def send_snapshot_alerts(self, snapshots: list[PositionSnapshot]) -> None:
        raise NotImplementedError


class NoopNotifier(Notifier):
    def send_snapshot_alerts(self, snapshots: list[PositionSnapshot]) -> None:
        pass


class TelegramNotifier(Notifier):
    _API_BASE = "https://api.telegram.org"

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id

    def send_snapshot_alerts(self, snapshots: list[PositionSnapshot]) -> None:
        messages = [format_alert(s) for s in snapshots if s.should_alert]
        if not messages:
            return
        self._send_message("\n\n".join(messages))

    def _send_message(self, text: str) -> None:
        self._send_message_to(self._chat_id, text)

    def _send_message_to(self, chat_id: str, text: str) -> None:
        url = f"{self._API_BASE}/bot{self._bot_token}/sendMessage"
        try:
            response = requests.post(
                url,
                json={"chat_id": chat_id, "text": text},
                timeout=10,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Telegram API error: HTTP {exc.response.status_code}"
            ) from None
        except requests.RequestException as exc:
            raise RuntimeError(f"Telegram request failed: {type(exc).__name__}") from None


def format_alert(snapshot: PositionSnapshot) -> str:
    position = snapshot.position
    quote = snapshot.quote
    return (
        f"{position.symbol} {position.name}\n"
        f"Price: {quote.currency} {quote.price:,.2f} ({quote.change_percent:+.2f}%)\n"
        f"Unrealized P/L: {quote.currency} {snapshot.unrealized_gain:,.2f} "
        f"({snapshot.unrealized_gain_percent:+.2f}%)"
    )


def format_daily_summary(snapshots: list[PositionSnapshot]) -> str:
    lines = ["📅 今日收盤總結\n"]
    total_daily_gain = 0.0
    total_market_value = 0.0

    for s in snapshots:
        daily_gain = s.market_value * (s.quote.change_percent / 100)
        total_daily_gain += daily_gain
        total_market_value += s.market_value
        sign = "▲" if daily_gain >= 0 else "▼"
        lines.append(
            f"{sign} {s.position.symbol} {s.position.name}\n"
            f"   今日: {s.quote.currency} {daily_gain:+,.2f} ({s.quote.change_percent:+.2f}%)\n"
            f"   未實現: {s.quote.currency} {s.unrealized_gain:+,.2f} ({s.unrealized_gain_percent:+.2f}%)"
        )

    sign = "▲" if total_daily_gain >= 0 else "▼"
    lines.append(f"\n{sign} 今日總損益：{total_daily_gain:+,.2f}")
    return "\n".join(lines)


def create_notifier(name: str, bot_token: str | None, chat_id: str | None) -> Notifier:
    if name == "none":
        return NoopNotifier()
    if name == "telegram":
        if not bot_token or not chat_id:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env"
            )
        return TelegramNotifier(bot_token, chat_id)
    raise ValueError(f"Unsupported notifier: {name!r}")
