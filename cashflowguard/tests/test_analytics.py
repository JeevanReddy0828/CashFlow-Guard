"""Tests for AR analytics and aging calculations."""

import pandas as pd
import pytest
from datetime import datetime, timedelta

from cashflowguard.analytics.aging import calculate_aging, get_aging_summary
from cashflowguard.analytics.ar_metrics import calculate_ar_summary, calculate_dso


# --- calculate_aging ---

def test_calculate_aging_adds_columns(mixed_invoices_df):
    result = calculate_aging(mixed_invoices_df)
    assert "days_overdue" in result.columns
    assert "aging_bucket" in result.columns


def test_calculate_aging_current_bucket(customers_df):
    """An invoice due in the future should land in 'current'."""
    future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    invoices = pd.DataFrame({
        "invoice_id": ["INV-FUT"],
        "customer_id": ["C001"],
        "invoice_amount": [1000.0],
        "issue_date": [(datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d")],
        "due_date": [future],
        "status": ["open"],
    })
    result = calculate_aging(invoices)
    assert result.iloc[0]["aging_bucket"] == "current"
    assert result.iloc[0]["days_overdue"] == 0


def test_calculate_aging_overdue_bucket():
    """An invoice 45 days overdue should land in '31-60'."""
    past = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
    invoices = pd.DataFrame({
        "invoice_id": ["INV-OLD"],
        "customer_id": ["C001"],
        "invoice_amount": [1000.0],
        "issue_date": [(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")],
        "due_date": [past],
        "status": ["open"],
    })
    result = calculate_aging(invoices)
    assert result.iloc[0]["aging_bucket"] == "31-60"


def test_calculate_aging_90_plus_bucket():
    past = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
    invoices = pd.DataFrame({
        "invoice_id": ["INV-VERY-OLD"],
        "customer_id": ["C001"],
        "invoice_amount": [1000.0],
        "issue_date": [(datetime.now() - timedelta(days=150)).strftime("%Y-%m-%d")],
        "due_date": [past],
        "status": ["open"],
    })
    result = calculate_aging(invoices)
    assert result.iloc[0]["aging_bucket"] == "90+"


def test_calculate_aging_row_count_preserved(mixed_invoices_df):
    result = calculate_aging(mixed_invoices_df)
    assert len(result) == len(mixed_invoices_df)


# --- get_aging_summary ---

def test_get_aging_summary_returns_dataframe(mixed_invoices_df):
    result = get_aging_summary(mixed_invoices_df)
    assert isinstance(result, pd.DataFrame)


def test_get_aging_summary_only_open_invoices(mixed_invoices_df):
    """Summary should only count open invoices; total_amount should exclude paid ones."""
    result = get_aging_summary(mixed_invoices_df)
    open_total = mixed_invoices_df[mixed_invoices_df["status"] == "open"]["invoice_amount"].sum()
    assert result["total_amount"].sum() == pytest.approx(open_total)


def test_get_aging_summary_has_required_columns(mixed_invoices_df):
    result = get_aging_summary(mixed_invoices_df)
    for col in ["aging_bucket", "total_amount", "invoice_count", "percentage"]:
        assert col in result.columns


def test_get_aging_summary_percentage_sums_to_100(mixed_invoices_df):
    result = get_aging_summary(mixed_invoices_df)
    assert result["percentage"].sum() == pytest.approx(100.0, abs=0.1)


# --- calculate_ar_summary ---

def test_calculate_ar_summary_returns_dict(mixed_invoices_df):
    result = calculate_ar_summary(mixed_invoices_df)
    assert isinstance(result, dict)


def test_calculate_ar_summary_total_ar(mixed_invoices_df):
    result = calculate_ar_summary(mixed_invoices_df)
    expected = mixed_invoices_df[mixed_invoices_df["status"] == "open"]["invoice_amount"].sum()
    assert result["total_ar"] == pytest.approx(expected)


def test_calculate_ar_summary_overdue_ar(mixed_invoices_df):
    """overdue_ar should be positive since mixed_invoices_df has overdue open invoices."""
    result = calculate_ar_summary(mixed_invoices_df)
    assert result["overdue_ar"] > 0


def test_calculate_ar_summary_overdue_percentage_range(mixed_invoices_df):
    result = calculate_ar_summary(mixed_invoices_df)
    assert 0 <= result["overdue_percentage"] <= 100


def test_calculate_ar_summary_total_invoices_positive(mixed_invoices_df):
    result = calculate_ar_summary(mixed_invoices_df)
    assert result["total_invoices"] > 0


def test_calculate_ar_summary_has_dso_and_cei(mixed_invoices_df):
    result = calculate_ar_summary(mixed_invoices_df)
    assert "dso" in result
    assert "cei" in result


# --- calculate_dso ---

def test_calculate_dso_returns_float(mixed_invoices_df):
    result = calculate_dso(mixed_invoices_df)
    assert isinstance(result, float)


def test_calculate_dso_no_sales_returns_zero():
    """When all invoices are outside the period, DSO should be 0."""
    far_past = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
    invoices = pd.DataFrame({
        "invoice_id": ["INV-OLD"],
        "customer_id": ["C001"],
        "invoice_amount": [1000.0],
        "issue_date": [far_past],
        "due_date": [far_past],
        "status": ["open"],
    })
    result = calculate_dso(invoices, period_days=90)
    assert result == 0.0


def test_calculate_dso_non_negative(mixed_invoices_df):
    assert calculate_dso(mixed_invoices_df) >= 0
