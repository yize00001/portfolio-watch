from __future__ import annotations

from portfolio_watch.models import PositionSnapshot


class TelegramNotifier:
    def __init__(self, bot_token: str | None, chat_id: str | None) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_snapshot_alerts(self, snapshots: list[PositionSnapshot]) -> None:
        if not self.enabled:
            return

        messages = [format_alert(snapshot) for snapshot in snapshots if snapshot.should_alert]
        if not messages:
            return

        self._send_message("\n\n".join(messages))

    def _send_message(self, text: str) -> None:
        import requests

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        response = requests.post(
            url,
            json={"chat_id": self.chat_id, "text": text},
            timeout=10,
        )
        response.raise_for_status()


def format_alert(snapshot: PositionSnapshot) -> str:
    position = snapshot.position
    quote = snapshot.quote
    return (
        f"{position.symbol} {position.name}\n"
        f"Price: {quote.currency} {quote.price:,.2f} ({quote.change_percent:+.2f}%)\n"
        f"Unrealized P/L: {quote.currency} {snapshot.unrealized_gain:,.2f} "
        f"({snapshot.unrealized_gain_percent:+.2f}%)"
    )
