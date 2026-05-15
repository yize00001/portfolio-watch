from pathlib import Path

from portfolio_watch.portfolio import load_positions
from portfolio_watch.pricing import MockPriceProvider
from portfolio_watch.watcher import build_snapshots


def test_load_positions_from_example_csv() -> None:
    positions = load_positions(Path("data/portfolio.example.csv"))

    assert positions
    assert positions[0].symbol == "2330.TW"
    assert positions[0].currency == "TWD"


def test_build_snapshots_calculates_unrealized_gain() -> None:
    positions = load_positions(Path("data/portfolio.example.csv"))
    snapshots = build_snapshots(positions, MockPriceProvider())

    assert snapshots[0].market_value > snapshots[0].cost_basis
    assert snapshots[0].unrealized_gain_percent == 8
