"""Invoice aging analysis for CashFlowGuard."""

from datetime import datetime
from typing import Optional

import pandas as pd

from cashflowguard.utils import get_aging_bucket


def calculate_aging(
    invoices_df: pd.DataFrame,
    as_of: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Calculate aging for all open invoices.
    
    Args:
        invoices_df: Invoices DataFrame
        as_of: Date to calculate aging as of (default: today)
        
    Returns:
        DataFrame with aging columns added
    """
    if as_of is None:
        as_of = datetime.now()
    
    # Work on a copy
    df = invoices_df.copy()
    
    # Parse dates robustly - always convert
    df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    
    # Calculate days overdue using vectorized operations
    time_diff = as_of - df["due_date"]
    df["days_overdue"] = time_diff.dt.days.fillna(0).clip(lower=0)
    
    # Get aging bucket (still needs apply since it's a categorization function)
    df["aging_bucket"] = df["days_overdue"].apply(get_aging_bucket)
    
    return df


def get_aging_summary(
    invoices_df: pd.DataFrame,
    as_of: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Get summary of AR by aging bucket.
    
    Args:
        invoices_df: Invoices DataFrame
        as_of: Date to calculate aging as of
        
    Returns:
        DataFrame with aging summary
    """
    # Calculate aging
    df = calculate_aging(invoices_df, as_of)
    
    # Filter to open invoices only
    df = df[df["status"] == "open"]
    
    # Group by aging bucket
    aging_summary = df.groupby("aging_bucket").agg({
        "invoice_amount": ["sum", "count"],
        "invoice_id": "count"
    }).reset_index()
    
    aging_summary.columns = ["aging_bucket", "total_amount", "amount_count", "invoice_count"]
    
    # Calculate percentages
    total_ar = aging_summary["total_amount"].sum()
    if total_ar > 0:
        aging_summary["percentage"] = (aging_summary["total_amount"] / total_ar * 100).round(2)
    else:
        aging_summary["percentage"] = 0.0
    
    # Order buckets correctly
    bucket_order = ["current", "1-15", "16-30", "31-60", "61-90", "90+"]
    aging_summary["bucket_order"] = aging_summary["aging_bucket"].map(
        {bucket: i for i, bucket in enumerate(bucket_order)}
    )
    aging_summary = aging_summary.sort_values("bucket_order").drop("bucket_order", axis=1)
    
    return aging_summary


def get_customer_aging(
    invoices_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    as_of: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Get aging breakdown by customer.
    
    Args:
        invoices_df: Invoices DataFrame
        customers_df: Customers DataFrame
        as_of: Date to calculate aging as of
        
    Returns:
        DataFrame with customer aging summary
    """
    # Calculate aging
    df = calculate_aging(invoices_df, as_of)
    
    # Filter to open invoices
    df = df[df["status"] == "open"]
    
    # Group by customer and aging bucket
    customer_aging = df.groupby(["customer_id", "aging_bucket"]).agg({
        "invoice_amount": "sum",
        "invoice_id": "count"
    }).reset_index()
    
    customer_aging.columns = ["customer_id", "aging_bucket", "total_amount", "invoice_count"]
    
    # Pivot to wide format
    customer_aging_wide = customer_aging.pivot(
        index="customer_id",
        columns="aging_bucket",
        values="total_amount"
    ).fillna(0)
    
    # Add total column
    customer_aging_wide["total_ar"] = customer_aging_wide.sum(axis=1)
    
    # Merge with customer names
    customer_aging_wide = customer_aging_wide.merge(
        customers_df[["customer_id", "name"]],
        on="customer_id",
        how="left"
    )
    
    # Reorder columns
    cols = ["customer_id", "name", "total_ar"]
    bucket_cols = [col for col in customer_aging_wide.columns 
                   if col not in ["customer_id", "name", "total_ar"]]
    customer_aging_wide = customer_aging_wide[cols + bucket_cols]
    
    # Sort by total AR descending
    customer_aging_wide = customer_aging_wide.sort_values("total_ar", ascending=False)
    
    return customer_aging_wide


def get_aging_trend(
    invoices_df: pd.DataFrame,
    payments_df: Optional[pd.DataFrame] = None,
    months: int = 6
) -> pd.DataFrame:
    """
    Get aging trend over time.
    
    Args:
        invoices_df: Invoices DataFrame
        payments_df: Payments DataFrame
        months: Number of months to analyze
        
    Returns:
        DataFrame with monthly aging trends
    """
    # Parse dates
    df = invoices_df.copy()
    df["issue_date"] = pd.to_datetime(df["issue_date"], errors='coerce')
    
    # Get month-end dates for last N months
    today = datetime.now()
    month_ends = pd.date_range(
        end=today,
        periods=months,
        freq="ME"  # Month end frequency
    )
    
    aging_trends = []
    
    for month_end in month_ends:
        # Calculate aging as of this month end
        month_df = calculate_aging(df, month_end)
        
        # Filter to invoices that existed at this point
        month_df = month_df[month_df["issue_date"] <= month_end]
        
        # Get open invoices (considering payments if available)
        if payments_df is not None and not payments_df.empty:
            # Mark invoices as paid if payment received before month_end
            payments_copy = payments_df.copy()
            payments_copy["payment_date"] = pd.to_datetime(payments_copy["payment_date"], errors='coerce')
            
            paid_invoices = payments_copy[
                payments_copy["payment_date"] <= month_end
            ]["invoice_id"].unique()
            
            month_df = month_df[~month_df["invoice_id"].isin(paid_invoices)]
        else:
            # Just use status
            month_df = month_df[month_df["status"] == "open"]
        
        # Get aging summary for this month
        summary = month_df.groupby("aging_bucket")["invoice_amount"].sum()
        summary["month"] = month_end.strftime("%Y-%m")
        summary["total_ar"] = summary.sum()
        
        aging_trends.append(summary.to_dict())
    
    return pd.DataFrame(aging_trends)