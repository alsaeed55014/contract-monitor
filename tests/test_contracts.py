from datetime import date, timedelta

import pytest

from src.core.contracts import ContractManager


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-07-14", date(2026, 7, 14)),
        ("Contract ends on July 14, 2026", date(2026, 7, 14)),
        ("14/07/2026 10:30 ص", date(2026, 7, 14)),
        ("not a date", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_date(value, expected):
    assert ContractManager.parse_date(value) == expected


@pytest.mark.parametrize(
    ("days_from_today", "status", "color"),
    [
        (-2, "expired", "red"),
        (0, "urgent", "red"),
        (7, "urgent", "orange"),
        (8, "warning", "yellow"),
        (30, "warning", "yellow"),
        (31, "active", "green"),
    ],
)
def test_calculate_status_boundaries(days_from_today, status, color):
    expiry = date.today() + timedelta(days=days_from_today)

    result = ContractManager.calculate_status(expiry.isoformat())

    assert result["status"] == status
    assert result["days"] == days_from_today
    assert result["color"] == color


def test_calculate_status_for_invalid_date():
    assert ContractManager.calculate_status("unknown") == {
        "status": "unknown",
        "days": None,
        "label_ar": "غير معروف",
        "label_en": "Unknown",
        "color": "grey",
    }
