"""Tests for ML feature engineering."""

import pandas as pd
import pytest
from datetime import datetime, timedelta

from cashflowguard.ml.features import (
    create_target_variable,
    engineer_features,
    get_feature_columns,
)


def test_get_feature_columns_count():
    assert len(get_feature_columns()) == 25


def test_get_feature_columns_contains_key_features():
    cols = get_feature_columns()
    for expected in [
        "days_until_due", "customer_late_rate", "credit_utilization",
        "amount_x_late_rate", "invoice_amount_log",
    ]:
        assert expected in cols


def test_engineer_features_returns_all_feature_columns(open_invoices_df, customers_df):
    result = engineer_features(open_invoices_df, customers_df)
    for col in get_feature_columns():
        assert col in result.columns, f"Missing feature column: {col}"


def test_engineer_features_row_count_preserved(open_invoices_df, customers_df):
    result = engineer_features(open_invoices_df, customers_df)
    assert len(result) == len(open_invoices_df)


def test_engineer_features_days_until_due_sign(open_invoices_df, customers_df):
    """Overdue invoices should have negative days_until_due, upcoming should be positive."""
    result = engineer_features(open_invoices_df, customers_df)
    # INV001 is 30 days overdue → negative
    inv001 = result[result["invoice_id"] == "INV001"].iloc[0]
    assert inv001["days_until_due"] < 0
    # INV002 is due in 15 days → positive
    inv002 = result[result["invoice_id"] == "INV002"].iloc[0]
    assert inv002["days_until_due"] > 0


def test_engineer_features_no_payments_sets_defaults(open_invoices_df, customers_df):
    """When no payment history, customer history features default to 0."""
    result = engineer_features(open_invoices_df, customers_df, payments_df=None)
    assert (result["customer_late_rate"] == 0.0).all()
    assert (result["customer_avg_days_late"] == 0.0).all()


def test_engineer_features_credit_utilization_range(open_invoices_df, customers_df):
    """credit_utilization should be clipped to [0, 2]."""
    result = engineer_features(open_invoices_df, customers_df)
    assert result["credit_utilization"].between(0, 2).all()


def test_engineer_features_invoice_type_encoding(open_invoices_df, customers_df):
    """invoice_type_recurring should be 1 for recurring, 0 otherwise."""
    result = engineer_features(open_invoices_df, customers_df)
    inv002 = result[result["invoice_id"] == "INV002"].iloc[0]
    assert inv002["invoice_type_recurring"] == 1
    inv001 = result[result["invoice_id"] == "INV001"].iloc[0]
    assert inv001["invoice_type_recurring"] == 0


def test_engineer_features_with_payments_computes_history(open_invoices_df, customers_df, payments_df):
    """With payments provided, customer_invoice_count should be > 0."""
    result = engineer_features(open_invoices_df, customers_df, payments_df=payments_df)
    assert (result["customer_invoice_count"] >= 1).all()


def test_engineer_features_missing_optional_columns(customers_df):
    """Invoices without invoice_type/channel columns should not raise errors."""
    today = datetime.now()
    invoices = pd.DataFrame({
        "invoice_id": ["INV001"],
        "customer_id": ["C001"],
        "invoice_amount": [1000.0],
        "issue_date": [(today - timedelta(days=30)).strftime("%Y-%m-%d")],
        "due_date": [(today + timedelta(days=10)).strftime("%Y-%m-%d")],
        "status": ["open"],
    })
    result = engineer_features(invoices, customers_df)
    assert "invoice_type_recurring" in result.columns
    assert result["invoice_type_recurring"].iloc[0] == 0
    assert result["channel_online"].iloc[0] == 0


# --- create_target_variable ---

def _make_labeled_data():
    today = datetime.now()
    invoices = pd.DataFrame({
        "invoice_id": ["INV-A", "INV-B", "INV-C"],
        "due_date": [
            (today - timedelta(days=30)).strftime("%Y-%m-%d"),  # INV-A: paid 20d late → late
            (today - timedelta(days=30)).strftime("%Y-%m-%d"),  # INV-B: paid 3d late → on time (< 7d)
            (today - timedelta(days=30)).strftime("%Y-%m-%d"),  # INV-C: unpaid
        ],
        "invoice_amount": [1000.0, 2000.0, 3000.0],
    })
    payments = pd.DataFrame({
        "invoice_id": ["INV-A", "INV-B"],
        "payment_date": [
            (today - timedelta(days=10)).strftime("%Y-%m-%d"),  # 20 days after due
            (today - timedelta(days=27)).strftime("%Y-%m-%d"),  # 3 days after due
        ],
    })
    return invoices, payments


def test_create_target_variable_late_invoice():
    invoices, payments = _make_labeled_data()
    result = create_target_variable(invoices, payments, late_threshold_days=7)
    inv_a = result[result["invoice_id"] == "INV-A"].iloc[0]
    assert inv_a["is_late"] == 1


def test_create_target_variable_on_time_invoice():
    invoices, payments = _make_labeled_data()
    result = create_target_variable(invoices, payments, late_threshold_days=7)
    inv_b = result[result["invoice_id"] == "INV-B"].iloc[0]
    assert inv_b["is_late"] == 0


def test_create_target_variable_unpaid_defaults_zero():
    invoices, payments = _make_labeled_data()
    result = create_target_variable(invoices, payments, late_threshold_days=7)
    inv_c = result[result["invoice_id"] == "INV-C"].iloc[0]
    assert inv_c["is_late"] == 0


def test_create_target_variable_threshold_respected():
    """A payment 5 days late with threshold=3 should be marked late."""
    today = datetime.now()
    invoices = pd.DataFrame({
        "invoice_id": ["INV-X"],
        "due_date": [(today - timedelta(days=10)).strftime("%Y-%m-%d")],
        "invoice_amount": [500.0],
    })
    payments = pd.DataFrame({
        "invoice_id": ["INV-X"],
        "payment_date": [(today - timedelta(days=5)).strftime("%Y-%m-%d")],  # 5 days late
    })
    result = create_target_variable(invoices, payments, late_threshold_days=3)
    assert result.iloc[0]["is_late"] == 1
