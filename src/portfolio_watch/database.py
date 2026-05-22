from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DB_PATH = Path("data/portfolio.db")


@dataclass
class Lot:
    symbol: str
    name: str
    quantity: float
    cost_per_share: float
    currency: str
    bought_on: str


@dataclass
class PortfolioRow:
    symbol: str
    name: str
    quantity: float
    average_cost: float
    currency: str
    alert_change_percent: float | None
    alert_gain_percent: float | None


@contextmanager
def _connect(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS lots (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol         TEXT    NOT NULL,
                name           TEXT    NOT NULL,
                quantity       REAL    NOT NULL,
                cost_per_share REAL    NOT NULL,
                currency       TEXT    NOT NULL DEFAULT 'TWD',
                bought_on      TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alert_settings (
                symbol               TEXT PRIMARY KEY,
                alert_change_percent REAL,
                alert_gain_percent   REAL
            );
        """)


def add_lot(
    symbol: str,
    name: str,
    quantity: float,
    cost_per_share: float,
    currency: str = "TWD",
    bought_on: str | None = None,
    db_path: Path = DB_PATH,
) -> None:
    on = bought_on or date.today().isoformat()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO lots (symbol, name, quantity, cost_per_share, currency, bought_on)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (symbol.upper(), name, quantity, cost_per_share, currency.upper(), on),
        )
        conn.execute(
            "INSERT OR IGNORE INTO alert_settings (symbol) VALUES (?)",
            (symbol.upper(),),
        )


def sell_shares(symbol: str, quantity: float, db_path: Path = DB_PATH) -> None:
    with _connect(db_path) as conn:
        current = _get_quantity(conn, symbol)
        if quantity > current:
            raise ValueError(
                f"Cannot sell {quantity} shares of {symbol}: only {current} held"
            )
        conn.execute(
            "INSERT INTO lots (symbol, name, quantity, cost_per_share, currency, bought_on)"
            " SELECT symbol, name, ?, 0, currency, ? FROM lots"
            " WHERE symbol = ? ORDER BY id DESC LIMIT 1",
            (-quantity, date.today().isoformat(), symbol.upper()),
        )


def get_positions(db_path: Path = DB_PATH) -> list[PortfolioRow]:
    with _connect(db_path) as conn:
        rows = conn.execute("""
            SELECT
                l.symbol,
                l.name,
                SUM(l.quantity)                                          AS quantity,
                SUM(CASE WHEN l.quantity > 0 THEN l.quantity * l.cost_per_share ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN l.quantity > 0 THEN l.quantity ELSE 0 END), 0)
                                                                         AS average_cost,
                l.currency,
                a.alert_change_percent,
                a.alert_gain_percent
            FROM lots l
            LEFT JOIN alert_settings a ON a.symbol = l.symbol
            GROUP BY l.symbol
            HAVING SUM(l.quantity) > 0
        """).fetchall()
    return [
        PortfolioRow(
            symbol=r["symbol"],
            name=r["name"],
            quantity=r["quantity"],
            average_cost=r["average_cost"],
            currency=r["currency"],
            alert_change_percent=r["alert_change_percent"],
            alert_gain_percent=r["alert_gain_percent"],
        )
        for r in rows
    ]


def set_alert(
    symbol: str,
    alert_change_percent: float | None = None,
    alert_gain_percent: float | None = None,
    db_path: Path = DB_PATH,
) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO alert_settings (symbol, alert_change_percent, alert_gain_percent)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT(symbol) DO UPDATE SET"
            "   alert_change_percent = excluded.alert_change_percent,"
            "   alert_gain_percent   = excluded.alert_gain_percent",
            (symbol.upper(), alert_change_percent, alert_gain_percent),
        )


def _get_quantity(conn: sqlite3.Connection, symbol: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) AS qty FROM lots WHERE symbol = ?",
        (symbol.upper(),),
    ).fetchone()
    return row["qty"] if row else 0.0
