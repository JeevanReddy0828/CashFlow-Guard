"""Accounts Receivable metrics calculation."""

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from cashflowguard.utils import business_days_between, days_between


def calculate_dso(
    invoices_df: pd.DataFrame,
    payments_df: Optional[pd.DataFrame] = None,
    period_days: int = 90
) -> float:
    """
    Calculate Days Sales Outstanding (DSO).
    
    DSO = (Accounts Receivable / Total Credit Sales) × Number of Days
    
    Args:
        invoices_df: Invoices DataFrame
        payments_df: Payments DataFrame (optional)
        period_days: Period for calculation (default: 90 days)
        
    Returns:
        DSO in days
    """
    # Get current AR (open invoices)
    current_ar = invoices_df[invoices_df["status"] == "open"]["invoice_amount"].sum()
    
    # Get credit sales in the period
    df = invoices_df.copy()
    
    # Parse dates robustly
    if df["issue_date"].dtype == "object" or not pd.api.types.is_datetime64_any_dtype(df["issue_date"]):
        df["issue_date"] = pd.to_datetime(df["issue_date"], errors='coerce')
    
    cutoff_date = datetime.now() - pd.Timedelta(days=period_days)
    period_sales = df[df["issue_date"] >= cutoff_date]["invoice_amount"].sum()
    
    if period_sales == 0:
        return 0.0
    
    dso = (current_ar / period_sales) * period_days
    return round(dso, 2)


def calculate_collection_effectiveness_index(
    invoices_df: pd.DataFrame,
    payments_df: Optional[pd.DataFrame] = None,
    period_days: int = 90
) -> float:
    """
    Calculate Collection Effectiveness Index (CEI).
    
    CEI = (Beginning AR + Credit Sales - Ending AR) / 
          (Beginning AR + Credit Sales - Ending Current AR) × 100
    
    Args:
        invoices_df: Invoices DataFrame
        payments_df: Payments DataFrame (optional)
        period_days: Period for calculation
        
    Returns:
        CEI as percentage
    """
    df = invoices_df.copy()
    
    # Parse dates robustly
    if df["issue_date"].dtype == "object" or not pd.api.types.is_datetime64_any_dtype(df["issue_date"]):
        df["issue_date"] = pd.to_datetime(df["issue_date"], errors='coerce')
    if df["due_date"].dtype == "object" or not pd.api.types.is_datetime64_any_dtype(df["due_date"]):
        df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    
    # Define period
    end_date = datetime.now()
    start_date = end_date - pd.Timedelta(days=period_days)
    
    # Beginning AR (all open invoices at start)
    beginning_ar = df[
        (df["issue_date"] < start_date) & 
        (df["status"] == "open")
    ]["invoice_amount"].sum()
    
    # Credit sales during period
    credit_sales = df[
        (df["issue_date"] >= start_date) & 
        (df["issue_date"] < end_date)
    ]["invoice_amount"].sum()
    
    # Ending AR (all open invoices at end)
    ending_ar = df[df["status"] == "open"]["invoice_amount"].sum()
    
    # Ending current AR (not yet due)
    ending_current_ar = df[
        (df["status"] == "open") & 
        (df["due_date"] >= end_date)
    ]["invoice_amount"].sum()
    
    denominator = beginning_ar + credit_sales - ending_current_ar
    
    if denominator == 0:
        return 100.0
    
    cei = ((beginning_ar + credit_sales - ending_ar) / denominator) * 100
    return round(max(0, min(100, cei)), 2)


def calculate_payment_behavior(
    invoices_df: pd.DataFrame,
    payments_df: Optional[pd.DataFrame] = None
) -> dict[str, float]:
    """
    Calculate payment behavior metrics.
    
    Args:
        invoices_df: Invoices DataFrame
        payments_df: Payments DataFrame
        
    Returns:
        Dictionary with payment behavior metrics
    """
    df = invoices_df.copy()
    
    # Parse dates robustly
    if df["issue_date"].dtype == "object" or not pd.api.types.is_datetime64_any_dtype(df["issue_date"]):
        df["issue_date"] = pd.to_datetime(df["issue_date"], errors='coerce')
    if df["due_date"].dtype == "object" or not pd.api.types.is_datetime64_any_dtype(df["due_date"]):
        df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    
    metrics = {}
    
    # Get paid invoices
    if payments_df is not None and not payments_df.empty:
        payments = payments_df.copy()
        if payments["payment_date"].dtype == "object" or not pd.api.types.is_datetime64_any_dtype(payments["payment_date"]):
            payments["payment_date"] = pd.to_datetime(payments["payment_date"], errors='coerce')
        
        # Merge invoices with payments
        paid_invoices = df.merge(
            payments[["invoice_id", "payment_date"]],
            on="invoice_id",
            how="inner"
        )
        
        # Calculate days to payment (vectorized)
        paid_invoices["days_to_payment"] = (paid_invoices["payment_date"] - paid_invoices["issue_date"]).dt.days
        paid_invoices["days_late"] = (paid_invoices["payment_date"] - paid_invoices["due_date"]).dt.days.clip(lower=0)
        
        # Metrics
        metrics["total_invoices"] = len(df)
        metrics["paid_invoices"] = len(paid_invoices)
        metrics["payment_rate"] = round(
            (len(paid_invoices) / len(df) * 100) if len(df) > 0 else 0, 2
        )
        
        metrics["avg_days_to_payment"] = round(paid_invoices["days_to_payment"].mean(), 2)
        metrics["median_days_to_payment"] = round(paid_invoices["days_to_payment"].median(), 2)
        
        # Late payment metrics
        late_invoices = paid_invoices[paid_invoices["days_late"] > 0]
        metrics["late_payment_count"] = len(late_invoices)
        metrics["late_payment_rate"] = round(
            (len(late_invoices) / len(paid_invoices) * 100) if len(paid_invoices) > 0 else 0, 2
        )
        
        if len(late_invoices) > 0:
            metrics["avg_days_late"] = round(late_invoices["days_late"].mean(), 2)
            metrics["median_days_late"] = round(late_invoices["days_late"].median(), 2)
            metrics["max_days_late"] = int(late_invoices["days_late"].max())
        else:
            metrics["avg_days_late"] = 0.0
            metrics["median_days_late"] = 0.0
            metrics["max_days_late"] = 0
    
    else:
        # Fallback without payment data
        metrics["total_invoices"] = len(df)
        metrics["paid_invoices"] = len(df[df["status"] == "paid"])
        metrics["payment_rate"] = round(
            (metrics["paid_invoices"] / metrics["total_invoices"] * 100) 
            if metrics["total_invoices"] > 0 else 0, 2
        )
    
    return metrics


def calculate_customer_risk_scores(
    invoices_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    payments_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Calculate risk scores for each customer.
    
    Risk factors:
    - Late payment history
    - Average days late
    - Outstanding balance
    - Concentration risk (% of total AR)
    
    Args:
        invoices_df: Invoices DataFrame
        customers_df: Customers DataFrame
        payments_df: Payments DataFrame
        
    Returns:
        DataFrame with customer risk scores
    """
    df = invoices_df.copy()
    
    # Parse dates robustly
    if df["due_date"].dtype == "object" or not pd.api.types.is_datetime64_any_dtype(df["due_date"]):
        df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    
    customer_metrics = []
    
    for customer_id in customers_df["customer_id"]:
        customer_invoices = df[df["customer_id"] == customer_id]
        
        if len(customer_invoices) == 0:
            continue
        
        metrics = {
            "customer_id": customer_id,
            "total_invoices": len(customer_invoices),
            "open_invoices": len(customer_invoices[customer_invoices["status"] == "open"]),
            "total_ar": customer_invoices[
                customer_invoices["status"] == "open"
            ]["invoice_amount"].sum(),
        }
        
        # Payment history analysis
        if payments_df is not None and not payments_df.empty:
            payments = payments_df.copy()
            if payments["payment_date"].dtype == "object" or not pd.api.types.is_datetime64_any_dtype(payments["payment_date"]):
                payments["payment_date"] = pd.to_datetime(payments["payment_date"], errors='coerce')
            
            paid_invoices = customer_invoices.merge(
                payments[["invoice_id", "payment_date"]],
                on="invoice_id",
                how="inner"
            )
            
            if len(paid_invoices) > 0:
                # Vectorized calculation
                paid_invoices["days_late"] = (paid_invoices["payment_date"] - paid_invoices["due_date"]).dt.days.clip(lower=0)
                
                metrics["paid_invoices"] = len(paid_invoices)
                metrics["late_invoices"] = len(paid_invoices[paid_invoices["days_late"] > 0])
                metrics["late_rate"] = round(
                    (metrics["late_invoices"] / metrics["paid_invoices"] * 100), 2
                )
                metrics["avg_days_late"] = round(paid_invoices["days_late"].mean(), 2)
            else:
                metrics["paid_invoices"] = 0
                metrics["late_invoices"] = 0
                metrics["late_rate"] = 0.0
                metrics["avg_days_late"] = 0.0
        else:
            metrics["paid_invoices"] = len(customer_invoices[customer_invoices["status"] == "paid"])
            metrics["late_invoices"] = 0
            metrics["late_rate"] = 0.0
            metrics["avg_days_late"] = 0.0
        
        customer_metrics.append(metrics)
    
    risk_df = pd.DataFrame(customer_metrics)
    
    # Calculate concentration risk
    total_ar = risk_df["total_ar"].sum()
    risk_df["ar_concentration"] = (
        (risk_df["total_ar"] / total_ar * 100) if total_ar > 0 else 0
    ).round(2)
    
    # Calculate risk score (0-100, higher = riskier)
    # Weighted components:
    # - Late rate (40%)
    # - Avg days late (30%)
    # - AR concentration (20%)
    # - Number of open invoices (10%)
    
    risk_df["risk_score"] = (
        (risk_df["late_rate"] * 0.4) +
        (np.minimum(risk_df["avg_days_late"] / 90 * 100, 100) * 0.3) +
        (np.minimum(risk_df["ar_concentration"], 100) * 0.2) +
        (np.minimum(risk_df["open_invoices"] / 10 * 100, 100) * 0.1)
    ).round(2)
    
    # Merge with customer names
    risk_df = risk_df.merge(
        customers_df[["customer_id", "name"]],
        on="customer_id",
        how="left"
    )
    
    # Sort by risk score descending
    risk_df = risk_df.sort_values("risk_score", ascending=False)
    
    return risk_df


def calculate_ar_summary(
    invoices_df: pd.DataFrame,
    payments_df: Optional[pd.DataFrame] = None
) -> dict[str, any]:
    """
    Calculate comprehensive AR summary.
    
    Args:
        invoices_df: Invoices DataFrame
        payments_df: Payments DataFrame
        
    Returns:
        Dictionary with AR summary metrics
    """
    df = invoices_df.copy()
    
    # Parse dates robustly - ALWAYS convert, don't check dtype
    df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    
    summary = {}
    
    # Total AR
    summary["total_ar"] = df[df["status"] == "open"]["invoice_amount"].sum()
    summary["total_invoices"] = len(df[df["status"] == "open"])
    
    # Overdue AR - now dates are guaranteed to be datetime
    today = pd.Timestamp.now()
    overdue_df = df[(df["status"] == "open") & (df["due_date"] < today)]
    summary["overdue_ar"] = overdue_df["invoice_amount"].sum()
    summary["overdue_invoices"] = len(overdue_df)
    summary["overdue_percentage"] = round(
        (summary["overdue_ar"] / summary["total_ar"] * 100) 
        if summary["total_ar"] > 0 else 0, 2
    )
    
    # DSO
    summary["dso"] = calculate_dso(invoices_df, payments_df)
    
    # CEI
    summary["cei"] = calculate_collection_effectiveness_index(invoices_df, payments_df)
    
    # Payment behavior
    payment_metrics = calculate_payment_behavior(invoices_df, payments_df)
    summary.update(payment_metrics)
    
    # Average invoice amount
    summary["avg_invoice_amount"] = round(
        df[df["status"] == "open"]["invoice_amount"].mean()
        if len(df[df["status"] == "open"]) > 0 else 0, 2
    )
    
    return summary