"""Tests for data validators."""

import pandas as pd
import pytest
from datetime import datetime

from cashflowguard.io.validators import validate_customers, validate_invoices, validate_payments


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_customers(n=1):
    return pd.DataFrame({
        "customer_id": [f"CUST-{i:03d}" for i in range(1, n + 1)],
        "name": [f"Company {i}" for i in range(1, n + 1)],
        "email": [f"co{i}@example.com" for i in range(1, n + 1)],
        "phone": ["555-0000"] * n,
        "industry": ["Tech"] * n,
        "country": ["US"] * n,
        "state": ["CA"] * n,
        "payment_terms_days": [30] * n,
        "credit_limit": [50000.0] * n,
        "created_at": ["2024-01-01"] * n,
    })


def _make_invoices(customer_ids, *, due_before_issue=False):
    records = []
    for i, cid in enumerate(customer_ids, start=1):
        issue = "2024-01-01"
        due = "2023-12-01" if due_before_issue else "2024-01-31"
        records.append({
            "invoice_id": f"INV-{i:03d}",
            "customer_id": cid,
            "issue_date": issue,
            "due_date": due,
            "invoice_amount": 1000.0,
            "currency": "USD",
            "status": "open",
            "invoice_type": "one_time",
            "channel": "online",
            "created_at": "2024-01-01",
        })
    return pd.DataFrame(records)


def _make_payments(invoice_ids):
    return pd.DataFrame({
        "payment_id": [f"PAY-{i:03d}" for i, _ in enumerate(invoice_ids, start=1)],
        "invoice_id": list(invoice_ids),
        "payment_date": ["2024-02-01"] * len(invoice_ids),
        "amount": [1000.0] * len(invoice_ids),
        "method": ["bank_transfer"] * len(invoice_ids),
        "status": ["completed"] * len(invoice_ids),
    })


def test_validate_customers_valid():
    """Test valid customers data."""
    df = pd.DataFrame({
        "customer_id": ["CUST-001"],
        "name": ["Test Co"],
        "email": ["test@test.com"],
        "phone": ["555-1234"],
        "industry": ["Tech"],
        "country": ["US"],
        "state": ["CA"],
        "payment_terms_days": [30],
        "credit_limit": [10000],
        "created_at": ["2024-01-01"]
    })
    
    result = validate_customers(df)
    assert result.is_valid


def test_validate_customers_missing_columns():
    """Test missing required columns."""
    df = pd.DataFrame({
        "customer_id": ["CUST-001"],
        "name": ["Test Co"]
    })
    
    result = validate_customers(df)
    assert not result.is_valid
    assert "Missing required columns" in result.errors[0]


def test_validate_customers_duplicates():
    """Test duplicate customer IDs."""
    df = pd.DataFrame({
        "customer_id": ["CUST-001", "CUST-001"],
        "name": ["Test Co", "Test Co 2"],
        "email": ["test@test.com", "test2@test.com"],
        "phone": ["555-1234", "555-5678"],
        "industry": ["Tech", "Tech"],
        "country": ["US", "US"],
        "state": ["CA", "CA"],
        "payment_terms_days": [30, 30],
        "credit_limit": [10000, 10000],
        "created_at": ["2024-01-01", "2024-01-01"]
    })
    
    result = validate_customers(df)
    assert not result.is_valid
    assert "Duplicate customer_ids" in result.errors[0]


# ---------------------------------------------------------------------------
# validate_invoices
# ---------------------------------------------------------------------------

def test_validate_invoices_valid():
    customers = _make_customers(2)
    invoices = _make_invoices(["CUST-001", "CUST-002"])
    result = validate_invoices(invoices, customers)
    assert result.is_valid


def test_validate_invoices_missing_columns():
    customers = _make_customers(1)
    bad = pd.DataFrame({"invoice_id": ["INV-001"], "customer_id": ["CUST-001"]})
    result = validate_invoices(bad, customers)
    assert not result.is_valid
    assert "Missing required columns" in result.errors[0]


def test_validate_invoices_duplicate_ids():
    customers = _make_customers(1)
    invoices = _make_invoices(["CUST-001"])
    invoices = pd.concat([invoices, invoices], ignore_index=True)
    result = validate_invoices(invoices, customers)
    assert not result.is_valid
    assert any("Duplicate invoice_ids" in e for e in result.errors)


def test_validate_invoices_orphan_customer():
    customers = _make_customers(1)  # only CUST-001
    invoices = _make_invoices(["CUST-999"])  # doesn't exist
    result = validate_invoices(invoices, customers)
    assert not result.is_valid
    assert any("non-existent customers" in e for e in result.errors)


def test_validate_invoices_due_before_issue():
    customers = _make_customers(1)
    invoices = _make_invoices(["CUST-001"], due_before_issue=True)
    result = validate_invoices(invoices, customers)
    assert not result.is_valid
    assert any("due_date before issue_date" in e for e in result.errors)


# ---------------------------------------------------------------------------
# validate_payments
# ---------------------------------------------------------------------------

def test_validate_payments_valid():
    customers = _make_customers(1)
    invoices = _make_invoices(["CUST-001"])
    payments = _make_payments(["INV-001"])
    result = validate_payments(payments, invoices)
    assert result.is_valid


def test_validate_payments_missing_columns():
    invoices = _make_invoices(["CUST-001"])
    bad = pd.DataFrame({"payment_id": ["PAY-001"]})
    result = validate_payments(bad, invoices)
    assert not result.is_valid
    assert "Missing required columns" in result.errors[0]


def test_validate_payments_duplicate_ids():
    invoices = _make_invoices(["CUST-001"])
    payments = _make_payments(["INV-001"])
    payments = pd.concat([payments, payments], ignore_index=True)
    result = validate_payments(payments, invoices)
    assert not result.is_valid
    assert any("Duplicate payment_ids" in e for e in result.errors)


def test_validate_payments_orphan_invoice():
    invoices = _make_invoices(["CUST-001"])
    payments = _make_payments(["INV-999"])  # doesn't exist
    result = validate_payments(payments, invoices)
    assert not result.is_valid
    assert any("non-existent invoices" in e for e in result.errors)


def test_validate_payments_overpayment_warning():
    invoices = _make_invoices(["CUST-001"])  # invoice_amount = 1000.0
    payments = pd.DataFrame({
        "payment_id": ["PAY-001"],
        "invoice_id": ["INV-001"],
        "payment_date": ["2024-02-01"],
        "amount": [2000.0],  # double the invoice amount
        "method": ["bank_transfer"],
        "status": ["completed"],
    })
    result = validate_payments(payments, invoices)
    assert result.is_valid  # overpayment is a warning, not an error
    assert any("exceed invoice amount" in w for w in result.warnings)
