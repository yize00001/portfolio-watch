from __future__ import annotations

from abc import ABC, abstractmethod

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


def create_price_provider(name: str) -> PriceProvider:
    if name == "mock":
        return MockPriceProvider()

    raise ValueError(f"Unsupported price provider: {name}")
