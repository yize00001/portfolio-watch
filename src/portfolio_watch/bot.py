from __future__ import annotations

import re
import time
import logging
from datetime import date
from pathlib import Path

import requests

from portfolio_watch.database import DB_PATH, add_lot, get_positions, init_db, sell_shares
from portfolio_watch.market_hours import is_weekday_market_time
from portfolio_watch.models import PositionSnapshot
from portfolio_watch.notifier import TelegramNotifier, format_daily_summary
from portfolio_watch.portfolio import load_positions, load_positions_from_db
from portfolio_watch.pricing import PriceProvider
from portfolio_watch.watcher import build_snapshots

logger = logging.getLogger(__name__)

_MARKET_CLOSE_HOUR = 13
_MARKET_CLOSE_MINUTE = 30
_SYMBOL_RE = re.compile(r'^[A-Z0-9]{1,10}(\.[A-Z]{1,4})?$')

HELP_TEXT = """\
📋 可用指令：

/status   — 目前持股現況
/summary  — 今日損益總結
/positions — 持股清單（含平均成本）

/buy SYMBOL NAME QTY COST [CURRENCY]
  範例：/buy 3481.TW 群創 20 38.5 TWD

/sell SYMBOL QTY
  範例：/sell 3481.TW 10

/help — 顯示此說明"""


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


def _format_positions(db_path: Path) -> str:
    rows = get_positions(db_path)
    if not rows:
        return "目前沒有持股紀錄。"
    lines = ["📂 目前持股：\n"]
    for r in rows:
        lines.append(
            f"{r.symbol} {r.name}\n"
            f"  持有：{r.quantity:.0f} 股｜均成本：{r.currency} {r.average_cost:,.2f}"
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
        db_path: Path = DB_PATH,
    ) -> None:
        self._notifier = notifier
        self._portfolio_file = portfolio_file
        self._price_provider = price_provider
        self._check_interval = check_interval
        self._db_path = db_path
        self._use_db = db_path.exists()
        self._offset = 0
        self._last_check: float = 0
        self._last_summary_date: date | None = None

    def run(self) -> None:
        logger.info("Bot started. DB mode: %s", self._use_db)
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
            self._dispatch(chat_id, text)

    def _dispatch(self, chat_id: str, text: str) -> None:
        cmd = text.split()[0].lower() if text else ""
        if cmd == "/status":
            self._send_status(chat_id)
        elif cmd == "/summary":
            self._send_summary(chat_id)
        elif cmd == "/positions":
            self._send_positions(chat_id)
        elif cmd == "/buy":
            self._handle_buy(chat_id, text)
        elif cmd == "/sell":
            self._handle_sell(chat_id, text)
        elif cmd == "/help":
            self._notifier._send_message_to(chat_id, HELP_TEXT)

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
        if self._use_db:
            positions = load_positions_from_db(self._db_path)
        else:
            positions = load_positions(self._portfolio_file)
        return build_snapshots(positions, self._price_provider)

    # --- query commands ---

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

    def _send_positions(self, chat_id: str) -> None:
        try:
            text = _format_positions(self._db_path)
            self._notifier._send_message_to(chat_id, text)
        except Exception as exc:
            self._notifier._send_message_to(chat_id, f"Error fetching positions: {exc}")

    # --- portfolio write commands ---

    def _handle_buy(self, chat_id: str, text: str) -> None:
        # /buy SYMBOL NAME QTY COST [CURRENCY]
        parts = text.split()
        if len(parts) < 5:
            self._notifier._send_message_to(
                chat_id, "用法：/buy SYMBOL NAME 數量 成本 [幣別]\n範例：/buy 3481.TW 群創 20 38.5 TWD"
            )
            return

        symbol = parts[1].upper()
        if not _SYMBOL_RE.match(symbol):
            self._notifier._send_message_to(chat_id, f"股票代號格式不正確：{symbol}")
            return

        name = parts[2]
        try:
            quantity = float(parts[3])
            cost = float(parts[4])
        except ValueError:
            self._notifier._send_message_to(chat_id, "數量和成本必須是數字。")
            return

        if quantity <= 0 or cost <= 0:
            self._notifier._send_message_to(chat_id, "數量和成本必須大於 0。")
            return

        currency = parts[5].upper() if len(parts) >= 6 else "TWD"

        try:
            if not self._use_db:
                init_db(self._db_path)
                self._use_db = True
            add_lot(symbol, name, quantity, cost, currency, db_path=self._db_path)
            self._notifier._send_message_to(
                chat_id,
                f"✅ 已新增\n{symbol} {name}\n買進 {quantity:.0f} 股 @ {currency} {cost:,.2f}"
            )
        except Exception as exc:
            self._notifier._send_message_to(chat_id, f"新增失敗：{exc}")

    def _handle_sell(self, chat_id: str, text: str) -> None:
        # /sell SYMBOL QTY
        parts = text.split()
        if len(parts) < 3:
            self._notifier._send_message_to(
                chat_id, "用法：/sell SYMBOL 數量\n範例：/sell 3481.TW 10"
            )
            return

        symbol = parts[1].upper()
        if not _SYMBOL_RE.match(symbol):
            self._notifier._send_message_to(chat_id, f"股票代號格式不正確：{symbol}")
            return

        try:
            quantity = float(parts[2])
        except ValueError:
            self._notifier._send_message_to(chat_id, "數量必須是數字。")
            return

        if quantity <= 0:
            self._notifier._send_message_to(chat_id, "數量必須大於 0。")
            return

        try:
            sell_shares(symbol, quantity, db_path=self._db_path)
            self._notifier._send_message_to(
                chat_id, f"✅ 已記錄賣出\n{symbol} {quantity:.0f} 股"
            )
        except ValueError as exc:
            self._notifier._send_message_to(chat_id, f"❌ {exc}")
        except Exception as exc:
            self._notifier._send_message_to(chat_id, f"賣出失敗：{exc}")

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
