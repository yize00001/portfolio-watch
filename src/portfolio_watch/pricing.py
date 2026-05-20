from __future__ import annotations

from abc import ABC, abstractmethod

import yfinance as yf

from portfolio_watch.models import Position, Quote


class PriceProvider(ABC):
    @abstractmethod
    def get_quote(self, position: Position) -> Quote:
        raise NotImplementedError


class MockPriceProvider(PriceProvider):
    def get_quote(self, position: Position) -> Quote:
        simulated_price = position.average_cost * 1.08
        return Quote(
            symbol=position.symbol,
            price=round(simulated_price, 2),
            change_percent=1.25,
            currency=position.currency,
        )


class YFinancePriceProvider(PriceProvider):
    def get_quote(self, position: Position) -> Quote:
        ticker = yf.Ticker(position.symbol)
        info = ticker.fast_info

        price = info.last_price
        prev_close = info.previous_close

        if price is None or prev_close is None:
            raise RuntimeError(f"yfinance returned no price data for {position.symbol!r}")

        change_percent = ((price - prev_close) / prev_close) * 100 if prev_close else 0.0

        return Quote(
            symbol=position.symbol,
            price=round(price, 4),
            change_percent=round(change_percent, 4),
            currency=position.currency,
        )


def create_price_provider(name: str) -> PriceProvider:
    if name == "mock":
        return MockPriceProvider()
    if name == "yfinance":
        return YFinancePriceProvider()

    raise ValueError(f"Unsupported price provider: {name}")
