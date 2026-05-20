from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from portfolio_watch.models import Position, PositionSnapshot, Quote
from portfolio_watch.notifier import (
    TelegramNotifier,
    NoopNotifier,
    create_notifier,
    format_alert,
)


def _make_snapshot(
    symbol: str = "2330.TW",
    price: float = 900.0,
    change_percent: float = 4.0,
    average_cost: float = 780.0,
    quantity: float = 10,
    alert_change_percent: float | None = 3.0,
) -> PositionSnapshot:
    position = Position(
        symbol=symbol,
        name="台積電",
        quantity=quantity,
        average_cost=average_cost,
        currency="TWD",
        alert_change_percent=alert_change_percent,
    )
    quote = Quote(symbol=symbol, price=price, change_percent=change_percent, currency="TWD")
    market_value = quantity * price
    cost_basis = quantity * average_cost
    unrealized_gain = market_value - cost_basis
    return PositionSnapshot(
        position=position,
        quote=quote,
        market_value=market_value,
        cost_basis=cost_basis,
        unrealized_gain=unrealized_gain,
        unrealized_gain_percent=(unrealized_gain / cost_basis) * 100,
    )


class TestTelegramNotifier:
    def test_sends_message_when_alert_triggered(self) -> None:
        snapshot = _make_snapshot(change_percent=4.0, alert_change_percent=3.0)
        assert snapshot.should_alert

        with patch("portfolio_watch.notifier.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            TelegramNotifier("fake-token", "12345").send_snapshot_alerts([snapshot])

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        # Token must appear only in URL, never in the message body
        body = call_kwargs.kwargs["json"]["text"]
        assert "fake-token" not in body

    def test_skips_send_when_no_alert_triggered(self) -> None:
        snapshot = _make_snapshot(change_percent=1.0, alert_change_percent=3.0)
        assert not snapshot.should_alert

        with patch("portfolio_watch.notifier.requests.post") as mock_post:
            TelegramNotifier("fake-token", "12345").send_snapshot_alerts([snapshot])

        mock_post.assert_not_called()

    def test_http_error_does_not_leak_token(self) -> None:
        snapshot = _make_snapshot(change_percent=4.0, alert_change_percent=3.0)

        mock_response = MagicMock()
        mock_response.status_code = 401
        http_error = requests.HTTPError(response=mock_response)

        with patch("portfolio_watch.notifier.requests.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = http_error
            with pytest.raises(RuntimeError) as exc_info:
                TelegramNotifier("secret-token", "12345").send_snapshot_alerts([snapshot])

        assert "secret-token" not in str(exc_info.value)
        assert "401" in str(exc_info.value)


class TestCreateNotifier:
    def test_none_returns_noop(self) -> None:
        assert isinstance(create_notifier("none", None, None), NoopNotifier)

    def test_telegram_raises_without_credentials(self) -> None:
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            create_notifier("telegram", None, None)

    def test_telegram_returns_notifier_with_credentials(self) -> None:
        notifier = create_notifier("telegram", "token", "chat_id")
        assert isinstance(notifier, TelegramNotifier)

    def test_unknown_notifier_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported notifier"):
            create_notifier("line", None, None)
