"""Cash flow forecasting module."""

from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd


def forecast_cash_inflows(
    invoices_df: pd.DataFrame,
    payments_df: Optional[pd.DataFrame] = None,
    forecast_days: int = 30,
    as_of: Optional[datetime] = None
) -> dict[str, float]:
    """
    Forecast expected cash inflows.
    
    Uses historical payment patterns to predict when open invoices will be paid.
    
    Args:
        invoices_df: Invoices DataFrame
        payments_df: Payments DataFrame (for historical patterns)
        forecast_days: Number of days to forecast
        as_of: Forecast as of this date
        
    Returns:
        Dictionary with forecasts for 7, 14, and 30 days
    """
    if as_of is None:
        as_of = datetime.now()
    
    df = invoices_df.copy()
    
    # Parse dates robustly
    df["issue_date"] = pd.to_datetime(df["issue_date"], errors='coerce')
    df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    
    # Get open invoices
    open_invoices = df[df["status"] == "open"].copy()
    
    # Calculate historical payment patterns
    if payments_df is not None and not payments_df.empty:
        payment_pattern = _calculate_payment_pattern(df, payments_df)
    else:
        # Default pattern: 80% pay within 7 days of due date
        payment_pattern = {
            "avg_days_after_due": 7,
            "std_days_after_due": 14,
            "payment_probability": 0.8
        }
    
    # Forecast for each invoice
    forecasts = {7: 0.0, 14: 0.0, 30: 0.0}
    
    for _, invoice in open_invoices.iterrows():
        # Expected payment date = due_date + avg_days_after_due
        expected_payment_date = invoice["due_date"] + pd.Timedelta(
            days=int(payment_pattern["avg_days_after_due"])
        )
        
        days_until_payment = (expected_payment_date - as_of).days
        
        # Probability weight (accounts for uncertainty)
        probability = payment_pattern["payment_probability"]
        
        # Add to appropriate forecast buckets
        if days_until_payment <= 7:
            forecasts[7] += invoice["invoice_amount"] * probability
        if days_until_payment <= 14:
            forecasts[14] += invoice["invoice_amount"] * probability
        if days_until_payment <= 30:
            forecasts[30] += invoice["invoice_amount"] * probability
    
    # Round to 2 decimals
    forecasts = {k: round(v, 2) for k, v in forecasts.items()}
    
    return forecasts


def _calculate_payment_pattern(
    invoices_df: pd.DataFrame,
    payments_df: pd.DataFrame
) -> dict[str, float]:
    """
    Calculate historical payment patterns.
    
    Args:
        invoices_df: Invoices DataFrame
        payments_df: Payments DataFrame
        
    Returns:
        Dictionary with payment pattern metrics
    """
    df = invoices_df.copy()
    payments = payments_df.copy()
    
    # Parse dates robustly
    df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    payments["payment_date"] = pd.to_datetime(payments["payment_date"], errors='coerce')
    
    # Merge to get payment dates
    merged = df.merge(
        payments[["invoice_id", "payment_date"]],
        on="invoice_id",
        how="inner"
    )
    
    if len(merged) == 0:
        return {
            "avg_days_after_due": 7,
            "std_days_after_due": 14,
            "payment_probability": 0.8
        }
    
    # Calculate days after due date using vectorized operations
    merged["days_after_due"] = (merged["payment_date"] - merged["due_date"]).dt.days
    
    pattern = {
        "avg_days_after_due": merged["days_after_due"].mean(),
        "std_days_after_due": merged["days_after_due"].std(),
        "payment_probability": len(merged) / len(df) if len(df) > 0 else 0.8
    }
    
    return pattern


def simulate_cash_scenarios(
    invoices_df: pd.DataFrame,
    payments_df: Optional[pd.DataFrame] = None,
    n_scenarios: int = 100,
    days_ahead: int = 30
) -> pd.DataFrame:
    """
    Run Monte Carlo simulation for cash flow scenarios.
    
    Args:
        invoices_df: Invoices DataFrame
        payments_df: Payments DataFrame
        n_scenarios: Number of scenarios to simulate
        days_ahead: Forecast horizon in days
        
    Returns:
        DataFrame with scenario results
    """
    df = invoices_df.copy()
    
    # Parse dates robustly
    df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    
    # Get payment pattern
    if payments_df is not None and not payments_df.empty:
        pattern = _calculate_payment_pattern(df, payments_df)
    else:
        pattern = {
            "avg_days_after_due": 7,
            "std_days_after_due": 14,
            "payment_probability": 0.8
        }
    
    # Get open invoices
    open_invoices = df[df["status"] == "open"]
    
    scenarios = []
    now = pd.Timestamp.now()
    
    for scenario in range(n_scenarios):
        total_collected = 0
        
        for _, invoice in open_invoices.iterrows():
            # Simulate whether this invoice gets paid
            if np.random.random() < pattern["payment_probability"]:
                # Simulate payment delay (days after due date)
                delay = max(
                    0,
                    np.random.normal(
                        pattern["avg_days_after_due"],
                        pattern["std_days_after_due"]
                    )
                )
                
                # Calculate payment date
                payment_date = invoice["due_date"] + pd.Timedelta(days=int(delay))
                days_until_payment = (payment_date - now).days
                
                # If payment happens within forecast horizon, add to total
                if 0 <= days_until_payment <= days_ahead:
                    total_collected += invoice["invoice_amount"]
        
        scenarios.append({
            "scenario": scenario + 1,
            "total_collected": round(total_collected, 2),
            "days_ahead": days_ahead
        })
    
    scenarios_df = pd.DataFrame(scenarios)
    
    return scenarios_df


def analyze_collection_impact(
    invoices_df: pd.DataFrame,
    target_invoice_ids: list[str],
    success_probability: float = 0.9
) -> dict[str, float]:
    """
    Analyze cash impact of collecting specific invoices.
    
    Args:
        invoices_df: Invoices DataFrame
        target_invoice_ids: List of invoice IDs to target
        success_probability: Probability of successful collection
        
    Returns:
        Dictionary with impact analysis
    """
    df = invoices_df.copy()
    
    # Get targeted invoices
    targeted = df[df["invoice_id"].isin(target_invoice_ids)]
    
    # Calculate potential impact
    total_amount = targeted["invoice_amount"].sum()
    expected_collection = total_amount * success_probability
    
    impact = {
        "total_targeted": round(total_amount, 2),
        "expected_collection": round(expected_collection, 2),
        "success_probability": success_probability,
        "invoice_count": len(targeted)
    }
    
    return impact


def calculate_cash_gap(
    invoices_df: pd.DataFrame,
    forecast_days: int = 30
) -> dict[str, float]:
    """
    Calculate cash gap (AR - expected collections).
    
    Args:
        invoices_df: Invoices DataFrame
        forecast_days: Forecast horizon
        
    Returns:
        Dictionary with cash gap analysis
    """
    df = invoices_df.copy()
    
    # Parse dates
    df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    
    # Total AR
    open_invoices = df[df["status"] == "open"]
    total_ar = open_invoices["invoice_amount"].sum()
    
    # Expected collections (invoices due within forecast period)
    now = pd.Timestamp.now()
    forecast_end = now + pd.Timedelta(days=forecast_days)
    
    due_soon = open_invoices[
        (open_invoices["due_date"] >= now) &
        (open_invoices["due_date"] <= forecast_end)
    ]
    expected_collections = due_soon["invoice_amount"].sum() * 0.8  # 80% collection rate
    
    # Calculate gap
    cash_gap = total_ar - expected_collections
    
    gap_analysis = {
        "total_ar": round(total_ar, 2),
        "expected_collections": round(expected_collections, 2),
        "cash_gap": round(cash_gap, 2),
        "gap_percentage": round((cash_gap / total_ar * 100) if total_ar > 0 else 0, 2),
        "forecast_days": forecast_days
    }
    
    return gap_analysis