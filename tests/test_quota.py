"""Tests for quota tracking."""

from datetime import date
from unittest.mock import patch

import pytest

from youtube_mcp.utils.quota import QuotaExhaustedError, QuotaTracker


def test_initial_state():
    tracker = QuotaTracker(daily_limit=10_000)
    assert tracker.used == 0
    assert tracker.remaining == 10_000


def test_consume_list():
    tracker = QuotaTracker()
    tracker.consume("list")
    assert tracker.used == 1


def test_consume_search():
    tracker = QuotaTracker()
    tracker.consume("search")
    assert tracker.used == 100


def test_consume_multiple():
    tracker = QuotaTracker()
    tracker.consume("list")
    tracker.consume("search")
    tracker.consume("list", count=3)
    assert tracker.used == 104  # 1 + 100 + 3


def test_exhaust_quota():
    tracker = QuotaTracker(daily_limit=50)
    tracker.consume("list", count=50)
    with pytest.raises(QuotaExhaustedError) as exc_info:
        tracker.consume("list")
    assert exc_info.value.used == 50
    assert exc_info.value.limit == 50


def test_exhaust_quota_search():
    tracker = QuotaTracker(daily_limit=150)
    tracker.consume("search")  # 100
    with pytest.raises(QuotaExhaustedError):
        tracker.consume("search")  # would be 200, over 150


def test_status():
    tracker = QuotaTracker(daily_limit=10_000)
    tracker.consume("search")
    status = tracker.status()
    assert status["used"] == 100
    assert status["remaining"] == 9_900
    assert status["limit"] == 10_000
    assert status["date"] == str(date.today())


def test_resets_on_new_day():
    tracker = QuotaTracker(daily_limit=10_000)
    tracker.consume("search")
    assert tracker.used == 100

    # Simulate next day
    with patch("youtube_mcp.utils.quota.date") as mock_date:
        tomorrow = date(2099, 1, 1)
        mock_date.today.return_value = tomorrow
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        assert tracker.used == 0
        assert tracker.remaining == 10_000


def test_unknown_operation_defaults_to_1():
    tracker = QuotaTracker()
    tracker.consume("some_unknown_op")
    assert tracker.used == 1
