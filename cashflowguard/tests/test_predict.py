"""Tests for ML scoring and risk categorization."""

import pandas as pd
import pytest

from cashflowguard.ml.predict import _categorize_risk, _fallback_risk_scoring, score_invoices


# --- _categorize_risk ---

@pytest.mark.parametrize("score,expected", [
    (0,   "low"),
    (15,  "low"),
    (30,  "low"),
    (31,  "medium"),
    (45,  "medium"),
    (60,  "medium"),
    (61,  "high"),
    (75,  "high"),
    (85,  "high"),
    (86,  "very_high"),
    (100, "very_high"),
])
def test_categorize_risk_boundaries(score, expected):
    assert _categorize_risk(score) == expected


# --- _fallback_risk_scoring ---

def test_fallback_scoring_output_columns(mixed_invoices_df, customers_df, payments_df):
    result = _fallback_risk_scoring(mixed_invoices_df, customers_df, payments_df)
    assert "risk_score" in result.columns
    assert "risk_category" in result.columns


def test_fallback_scoring_only_open_invoices(mixed_invoices_df, customers_df, payments_df):
    result = _fallback_risk_scoring(mixed_invoices_df, customers_df, payments_df)
    assert (result["status"] == "open").all()
    # mixed_invoices_df has 1 paid invoice (INV002), so result should have 4 rows
    assert len(result) == 4


def test_fallback_scoring_sorted_descending(mixed_invoices_df, customers_df, payments_df):
    result = _fallback_risk_scoring(mixed_invoices_df, customers_df, payments_df)
    scores = result["risk_score"].tolist()
    assert scores == sorted(scores, reverse=True)


def test_fallback_scoring_risk_score_range(mixed_invoices_df, customers_df, payments_df):
    result = _fallback_risk_scoring(mixed_invoices_df, customers_df, payments_df)
    assert result["risk_score"].between(0, 100).all()


def test_fallback_scoring_overdue_higher_than_current(mixed_invoices_df, customers_df, payments_df):
    """Overdue invoices should generally score higher than future-due ones."""
    result = _fallback_risk_scoring(mixed_invoices_df, customers_df, payments_df)
    # INV001 is 60 days overdue; INV004 is due in 15 days
    inv001_score = result[result["invoice_id"] == "INV001"]["risk_score"].iloc[0]
    inv004_score = result[result["invoice_id"] == "INV004"]["risk_score"].iloc[0]
    assert inv001_score > inv004_score


def test_fallback_scoring_risk_categories_valid(mixed_invoices_df, customers_df, payments_df):
    result = _fallback_risk_scoring(mixed_invoices_df, customers_df, payments_df)
    valid = {"low", "medium", "high", "very_high"}
    assert set(result["risk_category"]).issubset(valid)


# --- score_invoices (fallback path, no model) ---

def test_score_invoices_no_model_returns_df(mixed_invoices_df, customers_df, payments_df):
    result = score_invoices(mixed_invoices_df, customers_df, payments_df)
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0


def test_score_invoices_no_model_has_risk_columns(mixed_invoices_df, customers_df, payments_df):
    result = score_invoices(mixed_invoices_df, customers_df, payments_df)
    assert "risk_score" in result.columns
    assert "risk_category" in result.columns


def test_score_invoices_all_paid_returns_empty(customers_df, payments_df):
    """When all invoices are paid, score_invoices returns an empty-ish result."""
    today = pd.Timestamp.now()
    all_paid = pd.DataFrame({
        "invoice_id": ["INV-P1", "INV-P2"],
        "customer_id": ["C001", "C002"],
        "invoice_amount": [1000.0, 2000.0],
        "issue_date": [(today - pd.Timedelta(days=60)).strftime("%Y-%m-%d")] * 2,
        "due_date": [(today - pd.Timedelta(days=30)).strftime("%Y-%m-%d")] * 2,
        "status": ["paid", "paid"],
        "currency": ["USD", "USD"],
    })
    result = score_invoices(all_paid, customers_df, payments_df)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


def test_score_invoices_nonexistent_model_path_uses_fallback(
    tmp_path, mixed_invoices_df, customers_df, payments_df
):
    fake_path = tmp_path / "nonexistent.pkl"
    result = score_invoices(mixed_invoices_df, customers_df, payments_df, model_path=fake_path)
    assert "risk_score" in result.columns
