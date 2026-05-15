from __future__ import annotations

from portfolio_watch.models import Position, PositionSnapshot
from portfolio_watch.pricing import PriceProvider


def build_snapshot(position: Position, price_provider: PriceProvider) -> PositionSnapshot:
    quote = price_provider.get_quote(position)
    market_value = position.quantity * quote.price
    cost_basis = position.quantity * position.average_cost
    unrealized_gain = market_value - cost_basis
    unrealized_gain_percent = (unrealized_gain / cost_basis) * 100 if cost_basis else 0

    return PositionSnapshot(
        position=position,
        quote=quote,
        market_value=market_value,
        cost_basis=cost_basis,
        unrealized_gain=unrealized_gain,
        unrealized_gain_percent=unrealized_gain_percent,
    )


def build_snapshots(
    positions: list[Position],
    price_provider: PriceProvider,
) -> list[PositionSnapshot]:
    return [build_snapshot(position, price_provider) for position in positions]
