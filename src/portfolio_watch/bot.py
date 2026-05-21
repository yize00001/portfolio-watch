from __future__ import annotations

import time
import logging
from datetime import date
from pathlib import Path

import requests

from portfolio_watch.market_hours import is_weekday_market_time
from portfolio_watch.models import PositionSnapshot
from portfolio_watch.notifier import TelegramNotifier, format_daily_summary
from portfolio_watch.portfolio import load_positions
from portfolio_watch.pricing import PriceProvider
from portfolio_watch.watcher import build_snapshots

logger = logging.getLogger(__name__)

_MARKET_CLOSE_HOUR = 13
_MARKET_CLOSE_MINUTE = 30


def _format_status(snapshots: list[PositionSnapshot], market_open: bool) -> str:
    header = "📊 Portfolio Status" if market_open else "📊 Portfolio Status (market closed)"
    lines = [header]
    for s in snapshots:
        lines.append(
            f"\n{s.position.symbol} {s.position.name}\n"
            f"Price: {s.quote.currency} {s.quote.price:,.2f} ({s.quote.change_percent:+.2f}%)\n"
            f"Unrealized P/L: {s.quote.currency} {s.unrealized_gain:,.2f}"
            f" ({s.unrealized_gain_percent:+.2f}%)"
        )
    return "\n".join(lines)


class PortfolioBot:
    _POLL_TIMEOUT = 30

    def __init__(
        self,
        notifier: TelegramNotifier,
        portfolio_file: Path,
        price_provider: PriceProvider,
        check_interval: int = 300,
    ) -> None:
        self._notifier = notifier
        self._portfolio_file = portfolio_file
        self._price_provider = price_provider
        self._check_interval = check_interval
        self._offset = 0
        self._last_check: float = 0
        self._last_summary_date: date | None = None

    def run(self) -> None:
        logger.info("Bot started. Send /status or /summary to query portfolio.")
        while True:
            try:
                self._handle_commands()
                self._maybe_check_alerts()
                self._maybe_send_close_summary()
            except Exception as exc:
                logger.error("Unexpected error: %s", exc)
            time.sleep(5)

    # --- command polling ---

    def _handle_commands(self) -> None:
        updates = self._get_updates()
        for update in updates:
            self._offset = update["update_id"] + 1
            message = update.get("message", {})
            text = message.get("text", "").strip()
            chat_id = str(message.get("chat", {}).get("id", ""))
            if chat_id != self._notifier._chat_id:
                continue
            if text == "/status":
                self._send_status(chat_id)
            elif text == "/summary":
                self._send_summary(chat_id)

    def _get_updates(self) -> list[dict]:
        url = f"{self._notifier._API_BASE}/bot{self._notifier._bot_token}/getUpdates"
        try:
            resp = requests.get(
                url,
                params={"offset": self._offset, "timeout": self._POLL_TIMEOUT},
                timeout=self._POLL_TIMEOUT + 5,
            )
            resp.raise_for_status()
            return resp.json().get("result", [])
        except requests.RequestException:
            return []

    def _fetch_snapshots(self) -> list[PositionSnapshot]:
        positions = load_positions(self._portfolio_file)
        return build_snapshots(positions, self._price_provider)

    def _send_status(self, chat_id: str) -> None:
        try:
            snapshots = self._fetch_snapshots()
            text = _format_status(snapshots, is_weekday_market_time())
            self._notifier._send_message_to(chat_id, text)
        except Exception as exc:
            self._notifier._send_message_to(chat_id, f"Error fetching status: {exc}")

    def _send_summary(self, chat_id: str) -> None:
        try:
            snapshots = self._fetch_snapshots()
            text = format_daily_summary(snapshots)
            self._notifier._send_message_to(chat_id, text)
        except Exception as exc:
            self._notifier._send_message_to(chat_id, f"Error fetching summary: {exc}")

    # --- scheduled alert check ---

    def _maybe_check_alerts(self) -> None:
        if not is_weekday_market_time():
            return
        if time.time() - self._last_check < self._check_interval:
            return
        self._last_check = time.time()
        try:
            snapshots = self._fetch_snapshots()
            self._notifier.send_snapshot_alerts(snapshots)
        except Exception as exc:
            logger.error("Alert check failed: %s", exc)

    # --- auto close summary at 13:30 ---

    def _maybe_send_close_summary(self) -> None:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("Asia/Taipei"))
        today = now.date()

        if now.weekday() >= 5:
            return
        if now.hour != _MARKET_CLOSE_HOUR or now.minute != _MARKET_CLOSE_MINUTE:
            return
        if self._last_summary_date == today:
            return

        self._last_summary_date = today
        try:
            snapshots = self._fetch_snapshots()
            text = format_daily_summary(snapshots)
            self._notifier._send_message(text)
            logger.info("Daily close summary sent.")
        except Exception as exc:
            logger.error("Close summary failed: %s", exc)
