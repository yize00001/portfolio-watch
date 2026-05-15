from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    symbol: str
    name: str
    quantity: float
    average_cost: float
    currency: str
    alert_change_percent: float | None = None
    alert_gain_percent: float | None = None


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    change_percent: float
    currency: str


@dataclass(frozen=True)
class PositionSnapshot:
    position: Position
    quote: Quote
    market_value: float
    cost_basis: float
    unrealized_gain: float
    unrealized_gain_percent: float

    @property
    def should_alert(self) -> bool:
        change_limit = self.position.alert_change_percent
        gain_limit = self.position.alert_gain_percent

        change_hit = change_limit is not None and abs(self.quote.change_percent) >= change_limit
        gain_hit = gain_limit is not None and abs(self.unrealized_gain_percent) >= gain_limit
        return change_hit or gain_hit
