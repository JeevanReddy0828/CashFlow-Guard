"""Tests for date and utility functions."""

import pytest
from datetime import datetime, timedelta

from cashflowguard.utils import (
    business_days_between,
    days_between,
    days_overdue,
    days_until_due,
    format_date,
    get_aging_bucket,
    get_month_start_end,
    get_quarter,
    is_weekend,
    parse_date,
)


# --- parse_date ---

@pytest.mark.parametrize("date_str,expected", [
    ("2024-01-15", datetime(2024, 1, 15)),
    ("2024/01/15", datetime(2024, 1, 15)),
    ("15-01-2024", datetime(2024, 1, 15)),
    ("15/01/2024", datetime(2024, 1, 15)),
    ("2024-01-15 10:30:00", datetime(2024, 1, 15, 10, 30, 0)),
    ("2024-01-15T10:30:00", datetime(2024, 1, 15, 10, 30, 0)),
])
def test_parse_date_formats(date_str, expected):
    assert parse_date(date_str) == expected


def test_parse_date_invalid_raises():
    with pytest.raises(ValueError, match="Unable to parse date"):
        parse_date("not-a-date")


# --- get_aging_bucket ---

@pytest.mark.parametrize("days,expected_bucket", [
    (0,   "current"),
    (-5,  "current"),   # negative = not yet overdue
    (1,   "1-15"),
    (15,  "1-15"),
    (16,  "16-30"),
    (30,  "16-30"),
    (31,  "31-60"),
    (60,  "31-60"),
    (61,  "61-90"),
    (90,  "61-90"),
    (91,  "90+"),
    (200, "90+"),
])
def test_get_aging_bucket(days, expected_bucket):
    assert get_aging_bucket(days) == expected_bucket


# --- days_between ---

def test_days_between_positive():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 31)
    assert days_between(start, end) == 30


def test_days_between_same_day():
    d = datetime(2024, 6, 15)
    assert days_between(d, d) == 0


def test_days_between_negative():
    start = datetime(2024, 1, 31)
    end = datetime(2024, 1, 1)
    assert days_between(start, end) == -30


# --- days_overdue ---

def test_days_overdue_past_due():
    due = datetime.now() - timedelta(days=10)
    result = days_overdue(due)
    assert result == 10


def test_days_overdue_not_yet_due():
    due = datetime.now() + timedelta(days=10)
    result = days_overdue(due)
    assert result == 0


def test_days_overdue_with_as_of():
    as_of = datetime(2024, 3, 1)
    due = datetime(2024, 2, 20)  # 10 days before as_of
    assert days_overdue(due, as_of=as_of) == 10


# --- days_until_due ---

def test_days_until_due_future():
    due = datetime.now() + timedelta(days=15)
    result = days_until_due(due)
    assert result > 0


def test_days_until_due_overdue():
    due = datetime.now() - timedelta(days=5)
    result = days_until_due(due)
    assert result < 0


def test_days_until_due_with_as_of():
    as_of = datetime(2024, 3, 1)
    due = datetime(2024, 3, 11)
    assert days_until_due(due, as_of=as_of) == 10


# --- is_weekend ---

def test_is_weekend_saturday():
    saturday = datetime(2024, 1, 6)  # Known Saturday
    assert is_weekend(saturday) is True


def test_is_weekend_sunday():
    sunday = datetime(2024, 1, 7)  # Known Sunday
    assert is_weekend(sunday) is True


def test_is_weekend_monday():
    monday = datetime(2024, 1, 8)  # Known Monday
    assert is_weekend(monday) is False


def test_is_weekend_friday():
    friday = datetime(2024, 1, 5)  # Known Friday
    assert is_weekend(friday) is False


# --- business_days_between ---

def test_business_days_between_full_week():
    # Monday to Friday = 5 business days (inclusive of both endpoints)
    start = datetime(2024, 1, 8)   # Monday
    end = datetime(2024, 1, 12)    # Friday
    result = business_days_between(start, end)
    assert result == 5


def test_business_days_between_across_weekend():
    # Friday to Monday = 2 business days
    friday = datetime(2024, 1, 12)
    monday = datetime(2024, 1, 15)
    result = business_days_between(friday, monday)
    assert result == 2


def test_business_days_between_same_day():
    d = datetime(2024, 1, 8)  # Monday
    assert business_days_between(d, d) == 1


def test_business_days_between_reversed_returns_zero():
    start = datetime(2024, 1, 12)
    end = datetime(2024, 1, 8)
    assert business_days_between(start, end) == 0


# --- get_quarter ---

@pytest.mark.parametrize("month,expected_quarter", [
    (1, 1), (2, 1), (3, 1),
    (4, 2), (5, 2), (6, 2),
    (7, 3), (8, 3), (9, 3),
    (10, 4), (11, 4), (12, 4),
])
def test_get_quarter(month, expected_quarter):
    assert get_quarter(datetime(2024, month, 1)) == expected_quarter


# --- get_month_start_end ---

def test_get_month_start_end_january():
    start, end = get_month_start_end(2024, 1)
    assert start == datetime(2024, 1, 1)
    assert end == datetime(2024, 1, 31)


def test_get_month_start_end_december():
    start, end = get_month_start_end(2024, 12)
    assert start == datetime(2024, 12, 1)
    assert end == datetime(2024, 12, 31)


def test_get_month_start_end_february_leap():
    start, end = get_month_start_end(2024, 2)  # 2024 is a leap year
    assert end == datetime(2024, 2, 29)


# --- format_date ---

def test_format_date():
    d = datetime(2024, 6, 5)
    assert format_date(d) == "2024-06-05"
