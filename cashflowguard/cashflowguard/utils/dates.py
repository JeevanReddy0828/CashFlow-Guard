"""Date and time utilities for CashFlowGuard."""

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd


def parse_date(date_str: str) -> datetime:
    """
    Parse a date string to datetime.
    
    Supports formats: YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY
    """
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_str}")


def days_between(start: datetime, end: datetime) -> int:
    """Calculate days between two dates."""
    return (end - start).days


def days_overdue(due_date: datetime, as_of: Optional[datetime] = None) -> int:
    """
    Calculate days overdue.
    
    Returns positive number if overdue, 0 if not yet due.
    """
    if as_of is None:
        as_of = datetime.now()
    
    days = days_between(due_date, as_of)
    return max(0, days)


def days_until_due(due_date: datetime, as_of: Optional[datetime] = None) -> int:
    """
    Calculate days until due.
    
    Returns positive number if not yet due, negative if overdue.
    """
    if as_of is None:
        as_of = datetime.now()
    
    return days_between(as_of, due_date)


def get_aging_bucket(days_overdue: int) -> str:
    """
    Categorize invoice into aging bucket.
    
    Buckets:
    - current: 0 days overdue
    - 1-15: 1-15 days overdue
    - 16-30: 16-30 days overdue
    - 31-60: 31-60 days overdue
    - 61-90: 61-90 days overdue
    - 90+: Over 90 days overdue
    """
    if days_overdue <= 0:
        return "current"
    elif days_overdue <= 15:
        return "1-15"
    elif days_overdue <= 30:
        return "16-30"
    elif days_overdue <= 60:
        return "31-60"
    elif days_overdue <= 90:
        return "61-90"
    else:
        return "90+"


def get_week_bounds(week_date: str) -> tuple[datetime, datetime]:
    """
    Get start and end of week (Monday-Sunday) for a given date.
    
    Args:
        week_date: Date string in YYYY-MM-DD format
        
    Returns:
        Tuple of (week_start, week_end)
    """
    date = parse_date(week_date)
    
    # Get Monday of the week
    days_since_monday = date.weekday()
    week_start = date - timedelta(days=days_since_monday)
    
    # Get Sunday of the week
    week_end = week_start + timedelta(days=6)
    
    return week_start, week_end


def get_month_start_end(year: int, month: int) -> tuple[datetime, datetime]:
    """Get first and last day of a month."""
    start = datetime(year, month, 1)
    
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(days=1)
    
    return start, end


def get_quarter(date: datetime) -> int:
    """Get quarter (1-4) for a date."""
    return (date.month - 1) // 3 + 1


def is_weekend(date: datetime) -> bool:
    """Check if date is weekend (Saturday or Sunday)."""
    return date.weekday() in [5, 6]


def business_days_between(start: datetime, end: datetime) -> int:
    """Calculate business days between two dates (excludes weekends)."""
    if start > end:
        return 0
    
    days = pd.bdate_range(start=start, end=end)
    return len(days)


def format_date(date: datetime) -> str:
    """Format datetime as YYYY-MM-DD string."""
    return date.strftime("%Y-%m-%d")


def format_datetime(date: datetime) -> str:
    """Format datetime as YYYY-MM-DD HH:MM:SS string."""
    return date.strftime("%Y-%m-%d %H:%M:%S")
