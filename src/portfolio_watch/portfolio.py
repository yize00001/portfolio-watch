from __future__ import annotations

import csv
from pathlib import Path

from portfolio_watch.database import DB_PATH, get_positions
from portfolio_watch.models import Position


def _optional_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    return float(value)


def load_positions_from_db(db_path: Path = DB_PATH) -> list[Position]:
    rows = get_positions(db_path)
    return [
        Position(
            symbol=r.symbol,
            name=r.name,
            quantity=r.quantity,
            average_cost=r.average_cost,
            currency=r.currency,
            alert_change_percent=r.alert_change_percent,
            alert_gain_percent=r.alert_gain_percent,
        )
        for r in rows
    ]


def load_positions(path: Path) -> list[Position]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        positions = []

        for row in reader:
            positions.append(
                Position(
                    symbol=row["symbol"].strip(),
                    name=row["name"].strip(),
                    quantity=float(row["quantity"]),
                    average_cost=float(row["average_cost"]),
                    currency=row.get("currency", "USD").strip() or "USD",
                    alert_change_percent=_optional_float(row.get("alert_change_percent")),
                    alert_gain_percent=_optional_float(row.get("alert_gain_percent")),
                )
            )

    return positions
