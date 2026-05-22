from __future__ import annotations

import pytest
from pathlib import Path

from portfolio_watch.database import (
    add_lot,
    get_positions,
    init_db,
    sell_shares,
    set_alert,
)


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    init_db(path)
    return path


def test_init_creates_db(db: Path) -> None:
    assert db.exists()


def test_add_lot_and_get_positions(db: Path) -> None:
    add_lot("2330.TW", "台積電", 10, 800.0, "TWD", db_path=db)
    rows = get_positions(db)

    assert len(rows) == 1
    assert rows[0].symbol == "2330.TW"
    assert rows[0].quantity == 10
    assert rows[0].average_cost == pytest.approx(800.0)
    assert rows[0].currency == "TWD"


def test_average_cost_weighted(db: Path) -> None:
    add_lot("2330.TW", "台積電", 10, 800.0, "TWD", db_path=db)
    add_lot("2330.TW", "台積電", 10, 900.0, "TWD", db_path=db)
    rows = get_positions(db)

    assert rows[0].average_cost == pytest.approx(850.0)
    assert rows[0].quantity == 20


def test_sell_shares_reduces_quantity(db: Path) -> None:
    add_lot("2330.TW", "台積電", 20, 800.0, "TWD", db_path=db)
    sell_shares("2330.TW", 5, db_path=db)
    rows = get_positions(db)

    assert rows[0].quantity == 15


def test_sell_all_shares_removes_position(db: Path) -> None:
    add_lot("2330.TW", "台積電", 10, 800.0, "TWD", db_path=db)
    sell_shares("2330.TW", 10, db_path=db)
    rows = get_positions(db)

    assert rows == []


def test_sell_more_than_held_raises(db: Path) -> None:
    add_lot("2330.TW", "台積電", 5, 800.0, "TWD", db_path=db)
    with pytest.raises(ValueError, match="Cannot sell"):
        sell_shares("2330.TW", 10, db_path=db)


def test_set_alert_and_retrieve(db: Path) -> None:
    add_lot("2330.TW", "台積電", 10, 800.0, "TWD", db_path=db)
    set_alert("2330.TW", alert_change_percent=3.0, alert_gain_percent=15.0, db_path=db)
    rows = get_positions(db)

    assert rows[0].alert_change_percent == pytest.approx(3.0)
    assert rows[0].alert_gain_percent == pytest.approx(15.0)


def test_symbol_normalized_to_uppercase(db: Path) -> None:
    add_lot("2330.tw", "台積電", 10, 800.0, "twd", db_path=db)
    rows = get_positions(db)

    assert rows[0].symbol == "2330.TW"
    assert rows[0].currency == "TWD"


def test_multiple_symbols(db: Path) -> None:
    add_lot("2330.TW", "台積電", 10, 800.0, "TWD", db_path=db)
    add_lot("0050.TW", "元大台灣50", 5, 150.0, "TWD", db_path=db)
    rows = get_positions(db)

    symbols = {r.symbol for r in rows}
    assert symbols == {"2330.TW", "0050.TW"}
