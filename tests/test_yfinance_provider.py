from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from portfolio_watch.models import Position
from portfolio_watch.pricing import YFinancePriceProvider


@pytest.fixture()
def tsmc_position() -> Position:
    return Position(
        symbol="2330.TW",
        name="台積電",
        quantity=100,
        average_cost=500.0,
        currency="TWD",
    )


def _make_fast_info(last_price: float, previous_close: float) -> SimpleNamespace:
    return SimpleNamespace(last_price=last_price, previous_close=previous_close)


def test_yfinance_returns_correct_quote(tsmc_position: Position) -> None:
    fake_info = _make_fast_info(last_price=550.0, previous_close=500.0)

    with patch("portfolio_watch.pricing.yf.Ticker") as mock_ticker_cls:
        mock_ticker_cls.return_value.fast_info = fake_info
        quote = YFinancePriceProvider().get_quote(tsmc_position)

    assert quote.symbol == "2330.TW"
    assert quote.price == 550.0
    assert quote.change_percent == pytest.approx(10.0)
    assert quote.currency == "TWD"


def test_yfinance_raises_on_missing_price(tsmc_position: Position) -> None:
    fake_info = _make_fast_info(last_price=None, previous_close=None)

    with patch("portfolio_watch.pricing.yf.Ticker") as mock_ticker_cls:
        mock_ticker_cls.return_value.fast_info = fake_info
        with pytest.raises(RuntimeError, match="no price data"):
            YFinancePriceProvider().get_quote(tsmc_position)
