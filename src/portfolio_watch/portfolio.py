from __future__ import annotations

import csv
from pathlib import Path

from portfolio_watch.models import Position


def _optional_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    return float(value)


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
