"""Feature engineering for late payment prediction - VECTORIZED VERSION."""

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd


def engineer_features(
    invoices_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    payments_df: Optional[pd.DataFrame] = None,
    as_of: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Engineer features for late payment prediction.
    
    Args:
        invoices_df: Invoices DataFrame
        customers_df: Customers DataFrame
        payments_df: Payments DataFrame (for historical features)
        as_of: Date to calculate features as of
        
    Returns:
        DataFrame with engineered features
    """
    if as_of is None:
        as_of = datetime.now()
    
    df = invoices_df.copy()
    
    # Parse dates robustly
    df["issue_date"] = pd.to_datetime(df["issue_date"], errors='coerce')
    df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    
    # === Time-based features (vectorized) ===
    as_of_ts = pd.Timestamp(as_of)
    df["days_until_due"] = (df["due_date"] - as_of_ts).dt.days
    df["days_since_issue"] = (as_of_ts - df["issue_date"]).dt.days
    
    # Invoice timing features
    df["issue_month"] = df["issue_date"].dt.month
    df["issue_quarter"] = df["issue_date"].dt.quarter
    df["issue_day_of_week"] = df["issue_date"].dt.dayofweek
    df["issue_is_weekend"] = (df["issue_date"].dt.dayofweek >= 5).astype(int)
    
    df["due_month"] = df["due_date"].dt.month
    df["due_quarter"] = df["due_date"].dt.quarter
    df["due_day_of_week"] = df["due_date"].dt.dayofweek
    df["due_is_weekend"] = (df["due_date"].dt.dayofweek >= 5).astype(int)
    
    # Payment term (vectorized)
    df["payment_term_days"] = (df["due_date"] - df["issue_date"]).dt.days
    
    # === Invoice amount features ===
    df["invoice_amount_log"] = np.log1p(df["invoice_amount"])
    df["invoice_amount_sqrt"] = np.sqrt(df["invoice_amount"])
    
    # Amount buckets
    df["amount_bucket"] = pd.cut(
        df["invoice_amount"],
        bins=[0, 1000, 5000, 10000, 50000, np.inf],
        labels=["tiny", "small", "medium", "large", "xlarge"]
    )
    
    # === Customer features ===
    customer_features = customers_df.set_index("customer_id")[
        ["payment_terms_days", "credit_limit"]
    ]
    df = df.merge(customer_features, left_on="customer_id", right_index=True, how="left")
    
    df["credit_limit_log"] = np.log1p(df["credit_limit"])
    df["credit_utilization"] = (df["invoice_amount"] / df["credit_limit"]).fillna(0)
    df["credit_utilization"] = df["credit_utilization"].clip(0, 2)  # Cap at 200%
    
    # === Historical customer behavior ===
    if payments_df is not None and not payments_df.empty:
        customer_history = _calculate_customer_history(invoices_df, payments_df, as_of)
        df = df.merge(customer_history, on="customer_id", how="left")
    else:
        # Default values when no payment history
        df["customer_invoice_count"] = 1
        df["customer_avg_days_late"] = 0.0
        df["customer_late_rate"] = 0.0
        df["customer_avg_payment_amount"] = df["invoice_amount"]
    
    # Fill NaN values for new customers
    df["customer_invoice_count"] = df["customer_invoice_count"].fillna(1)
    df["customer_avg_days_late"] = df["customer_avg_days_late"].fillna(0)
    df["customer_late_rate"] = df["customer_late_rate"].fillna(0)
    df["customer_avg_payment_amount"] = df["customer_avg_payment_amount"].fillna(
        df["invoice_amount"]
    )
    
    # === Categorical encodings ===
    # Invoice type - handle missing column gracefully
    if "invoice_type" in df.columns:
        df["invoice_type_recurring"] = (df["invoice_type"] == "recurring").astype(int)
        df["invoice_type_milestone"] = (df["invoice_type"] == "milestone").astype(int)
    else:
        df["invoice_type_recurring"] = 0
        df["invoice_type_milestone"] = 0
    
    # Channel - handle missing column gracefully
    if "channel" in df.columns:
        df["channel_online"] = (df["channel"] == "online").astype(int)
    else:
        df["channel_online"] = 0
    
    # === Concentration risk ===
    total_ar = df[df["status"] == "open"]["invoice_amount"].sum()
    customer_ar = df[df["status"] == "open"].groupby("customer_id")["invoice_amount"].sum()
    df = df.merge(
        customer_ar.rename("customer_total_ar"),
        left_on="customer_id",
        right_index=True,
        how="left"
    )
    df["customer_ar_concentration"] = (
        (df["customer_total_ar"] / total_ar * 100) if total_ar > 0 else 0
    ).fillna(0)
    
    # === Interaction features ===
    df["amount_x_days_until_due"] = df["invoice_amount_log"] * df["days_until_due"]
    df["amount_x_late_rate"] = df["invoice_amount_log"] * df["customer_late_rate"]
    df["utilization_x_late_rate"] = df["credit_utilization"] * df["customer_late_rate"]
    
    return df


def _calculate_customer_history(
    invoices_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    as_of: datetime
) -> pd.DataFrame:
    """
    Calculate historical payment behavior by customer (vectorized).
    
    Args:
        invoices_df: Invoices DataFrame
        payments_df: Payments DataFrame
        as_of: Calculate history as of this date
        
    Returns:
        DataFrame with customer history features
    """
    df = invoices_df.copy()
    payments = payments_df.copy()
    
    # Parse dates robustly
    df["issue_date"] = pd.to_datetime(df["issue_date"], errors='coerce')
    df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    payments["payment_date"] = pd.to_datetime(payments["payment_date"], errors='coerce')
    
    # Only consider invoices issued before as_of
    as_of_ts = pd.Timestamp(as_of)
    df = df[df["issue_date"] < as_of_ts]
    
    # If no historical invoices, return empty DataFrame
    if len(df) == 0:
        return pd.DataFrame(columns=[
            "customer_id", "customer_invoice_count", "customer_avg_days_late",
            "customer_late_rate", "customer_avg_payment_amount"
        ])
    
    # Merge with payments (use payment "amount" if exists, else invoice_amount)
    payment_cols = ["invoice_id", "payment_date"]
    if "amount" in payments.columns:
        payment_cols.append("amount")
    
    merged = df.merge(
        payments[payment_cols],
        on="invoice_id",
        how="left"
    )
    
    # Check if payment_date column exists before using it
    if "payment_date" not in merged.columns or len(merged) == 0:
        return pd.DataFrame(columns=[
            "customer_id", "customer_invoice_count", "customer_avg_days_late",
            "customer_late_rate", "customer_avg_payment_amount"
        ])
    
    # Only consider payments before as_of
    merged = merged[merged["payment_date"].isna() | (merged["payment_date"] < as_of_ts)]
    
    # If no payments in timeframe, return empty DataFrame
    if len(merged) == 0:
        return pd.DataFrame(columns=[
            "customer_id", "customer_invoice_count", "customer_avg_days_late",
            "customer_late_rate", "customer_avg_payment_amount"
        ])
    
    # Calculate days late (vectorized) - only for paid invoices
    paid_mask = merged["payment_date"].notna()
    merged["days_late"] = 0.0
    merged.loc[paid_mask, "days_late"] = (
        merged.loc[paid_mask, "payment_date"] - merged.loc[paid_mask, "due_date"]
    ).dt.days.clip(lower=0)
    
    # Group by customer
    agg_dict = {
        "invoice_id": "count",
        "days_late": "mean"
    }
    
    # Use payment amount if available, otherwise invoice amount
    if "amount" in merged.columns:
        agg_dict["amount"] = "mean"
        amount_col = "amount"
    else:
        agg_dict["invoice_amount"] = "mean"
        amount_col = "invoice_amount"
    
    customer_history = merged.groupby("customer_id").agg(agg_dict).reset_index()
    
    # Rename columns
    col_names = ["customer_id", "customer_invoice_count", "customer_avg_days_late", "customer_avg_payment_amount"]
    customer_history.columns = col_names
    
    # Calculate late rate
    late_counts = merged[merged["days_late"] > 0].groupby("customer_id").size()
    customer_history = customer_history.merge(
        late_counts.rename("late_count"),
        left_on="customer_id",
        right_index=True,
        how="left"
    )
    customer_history["late_count"] = customer_history["late_count"].fillna(0)
    customer_history["customer_late_rate"] = (
        customer_history["late_count"] / customer_history["customer_invoice_count"] * 100
    ).round(2)
    
    customer_history = customer_history.drop("late_count", axis=1)
    
    # Fill NaN values
    customer_history["customer_avg_days_late"] = customer_history["customer_avg_days_late"].fillna(0)
    
    return customer_history


def get_feature_columns() -> list[str]:
    """
    Get list of feature columns for modeling.
    
    Returns:
        List of feature column names
    """
    return [
        # Time features
        "days_until_due",
        "days_since_issue",
        "payment_term_days",
        "issue_month",
        "issue_quarter",
        "issue_day_of_week",
        "issue_is_weekend",
        "due_month",
        "due_quarter",
        "due_day_of_week",
        "due_is_weekend",
        
        # Amount features
        "invoice_amount_log",
        "invoice_amount_sqrt",
        "credit_limit_log",
        "credit_utilization",
        
        # Customer history
        "customer_invoice_count",
        "customer_avg_days_late",
        "customer_late_rate",
        "customer_ar_concentration",
        
        # Categorical
        "invoice_type_recurring",
        "invoice_type_milestone",
        "channel_online",
        
        # Interactions
        "amount_x_days_until_due",
        "amount_x_late_rate",
        "utilization_x_late_rate",
    ]


def create_target_variable(
    invoices_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    late_threshold_days: int = 7
) -> pd.DataFrame:
    """
    Create target variable for training (vectorized).
    
    Target: 1 if invoice paid > late_threshold_days after due date, 0 otherwise
    
    Args:
        invoices_df: Invoices DataFrame
        payments_df: Payments DataFrame
        late_threshold_days: Threshold for late payment
        
    Returns:
        DataFrame with target variable
    """
    df = invoices_df.copy()
    payments = payments_df.copy()
    
    # Parse dates robustly
    df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    payments["payment_date"] = pd.to_datetime(payments["payment_date"], errors='coerce')
    
    # Merge with payments
    df = df.merge(
        payments[["invoice_id", "payment_date"]],
        on="invoice_id",
        how="left"
    )
    
    # Calculate days late (vectorized) - only for paid invoices
    paid_mask = df["payment_date"].notna()
    df["days_late"] = 0.0
    df.loc[paid_mask, "days_late"] = (
        df.loc[paid_mask, "payment_date"] - df.loc[paid_mask, "due_date"]
    ).dt.days.clip(lower=0)
    
    # Create binary target
    df["is_late"] = (df["days_late"] > late_threshold_days).astype(int)
    
    return df


