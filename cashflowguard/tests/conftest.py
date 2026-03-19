"""Shared test fixtures."""

import pytest
import pandas as pd
from datetime import datetime, timedelta


def _today():
    return datetime.now()


@pytest.fixture
def customers_df():
    return pd.DataFrame({
        "customer_id": ["C001", "C002", "C003"],
        "name": ["Alpha Corp", "Beta Ltd", "Gamma Inc"],
        "email": ["a@alpha.com", "b@beta.com", "g@gamma.com"],
        "phone": ["555-1111", "555-2222", None],
        "industry": ["Tech", "Finance", "Retail"],
        "country": ["US", "US", "UK"],
        "state": ["CA", "NY", None],
        "payment_terms_days": [30, 45, 60],
        "credit_limit": [50000.0, 100000.0, 75000.0],
        "created_at": ["2023-01-01", "2023-01-01", "2023-01-01"],
    })


@pytest.fixture
def open_invoices_df():
    today = _today()
    return pd.DataFrame({
        "invoice_id": ["INV001", "INV002", "INV003", "INV004"],
        "customer_id": ["C001", "C001", "C002", "C003"],
        "invoice_amount": [5000.0, 2000.0, 15000.0, 8000.0],
        "issue_date": [
            (today - timedelta(days=60)).strftime("%Y-%m-%d"),
            (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            (today - timedelta(days=45)).strftime("%Y-%m-%d"),
            (today - timedelta(days=20)).strftime("%Y-%m-%d"),
        ],
        "due_date": [
            (today - timedelta(days=30)).strftime("%Y-%m-%d"),  # overdue
            (today + timedelta(days=15)).strftime("%Y-%m-%d"),  # upcoming
            (today - timedelta(days=10)).strftime("%Y-%m-%d"),  # overdue
            (today + timedelta(days=5)).strftime("%Y-%m-%d"),   # upcoming
        ],
        "status": ["open", "open", "open", "open"],
        "invoice_type": ["one_time", "recurring", "one_time", "milestone"],
        "channel": ["online", "online", "offline", "online"],
        "currency": ["USD", "USD", "USD", "USD"],
        "created_at": [
            (today - timedelta(days=60)).strftime("%Y-%m-%d"),
            (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            (today - timedelta(days=45)).strftime("%Y-%m-%d"),
            (today - timedelta(days=20)).strftime("%Y-%m-%d"),
        ],
    })


@pytest.fixture
def mixed_invoices_df():
    """Invoices with a mix of open and paid statuses."""
    today = _today()
    return pd.DataFrame({
        "invoice_id": ["INV001", "INV002", "INV003", "INV004", "INV005"],
        "customer_id": ["C001", "C001", "C002", "C002", "C003"],
        "invoice_amount": [5000.0, 2000.0, 15000.0, 3000.0, 8000.0],
        "issue_date": [
            (today - timedelta(days=90)).strftime("%Y-%m-%d"),
            (today - timedelta(days=60)).strftime("%Y-%m-%d"),
            (today - timedelta(days=45)).strftime("%Y-%m-%d"),
            (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            (today - timedelta(days=20)).strftime("%Y-%m-%d"),
        ],
        "due_date": [
            (today - timedelta(days=60)).strftime("%Y-%m-%d"),  # overdue open
            (today - timedelta(days=30)).strftime("%Y-%m-%d"),  # paid
            (today - timedelta(days=15)).strftime("%Y-%m-%d"),  # overdue open
            (today + timedelta(days=15)).strftime("%Y-%m-%d"),  # current open
            (today + timedelta(days=10)).strftime("%Y-%m-%d"),  # current open
        ],
        "status": ["open", "paid", "open", "open", "open"],
        "invoice_type": ["one_time", "one_time", "recurring", "one_time", "milestone"],
        "channel": ["online", "online", "offline", "online", "online"],
        "currency": ["USD", "USD", "USD", "USD", "USD"],
        "created_at": [
            (today - timedelta(days=90)).strftime("%Y-%m-%d"),
            (today - timedelta(days=60)).strftime("%Y-%m-%d"),
            (today - timedelta(days=45)).strftime("%Y-%m-%d"),
            (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            (today - timedelta(days=20)).strftime("%Y-%m-%d"),
        ],
    })


@pytest.fixture
def payments_df():
    today = _today()
    return pd.DataFrame({
        "payment_id": ["PAY001", "PAY002"],
        "invoice_id": ["INV001", "INV002"],
        "payment_date": [
            (today - timedelta(days=25)).strftime("%Y-%m-%d"),  # paid 5 days late (INV001 due -30d)
            (today - timedelta(days=25)).strftime("%Y-%m-%d"),  # paid early (INV002 due +15d)
        ],
        "amount": [5000.0, 2000.0],
        "method": ["bank_transfer", "credit_card"],
        "status": ["completed", "completed"],
    })
