"""Prediction and scoring module."""

from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
from datetime import datetime

from cashflowguard.ml.train import LatePaymentModel
from cashflowguard.utils.dates import days_overdue, days_between
import logging

logger = logging.getLogger(__name__)


def score_invoices(
    invoices_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    model_path: Optional[Path] = None,
    model: Optional[LatePaymentModel] = None,
) -> pd.DataFrame:
    """
    Score open invoices for late payment risk.
    
    Args:
        invoices_df: Invoices DataFrame
        customers_df: Customers DataFrame
        payments_df: Payments DataFrame
        model_path: Path to trained model file
        model: Pre-loaded model instance
        
    Returns:
        DataFrame with risk scores and categories
    """
    if model is None:
        if model_path is None or not model_path.exists():
            logger.warning("No model available - using fallback risk scoring")
            return _fallback_risk_scoring(invoices_df, customers_df, payments_df)
        
        model = LatePaymentModel.load(model_path)
    
    logger.info("Scoring invoices with ML model...")
    
    # Get open invoices
    open_invoices = invoices_df[invoices_df["status"] == "open"].copy()
    
    if len(open_invoices) == 0:
        logger.warning("No open invoices to score")
        return pd.DataFrame()
    
    # Engineer features
    from cashflowguard.ml.features import engineer_features
    features_df = engineer_features(
        open_invoices,
        customers_df,
        payments_df,
        pd.DataFrame()  # Empty actions for now
    )
    
    # Get predictions
    risk_scores = model.predict_proba(features_df)
    
    # Add to dataframe
    result = open_invoices.copy()
    result["risk_score"] = (risk_scores * 100).round(0).astype(int)
    result["risk_category"] = result["risk_score"].apply(_categorize_risk)
    
    # Sort by risk score descending
    result = result.sort_values("risk_score", ascending=False)
    
    logger.info(f"✓ Scored {len(result)} open invoices")
    
    return result


def _categorize_risk(score: float) -> str:
    """Categorize risk score into bins."""
    if score >= 86:
        return "very_high"
    elif score >= 61:
        return "high"
    elif score >= 31:
        return "medium"
    else:
        return "low"


def _safe_parse_date(date_value):
    """
    Safely parse date value to datetime, handling multiple formats.
    
    Args:
        date_value: String, datetime, or pd.Timestamp
        
    Returns:
        datetime object
    """
    if pd.isna(date_value):
        return pd.NaT
    
    # Already a datetime
    if isinstance(date_value, (datetime, pd.Timestamp)):
        return date_value
    
    # Parse string
    if isinstance(date_value, str):
        try:
            return pd.to_datetime(date_value)
        except:
            return pd.NaT
    
    return pd.NaT


def _calculate_days_overdue(due_date, as_of=None):
    """
    Calculate days overdue, handling both datetime and string dates.
    
    Args:
        due_date: Due date (datetime or string)
        as_of: Current date (defaults to now)
        
    Returns:
        Number of days overdue (0 if not overdue)
    """
    if as_of is None:
        as_of = datetime.now()
    
    # Ensure due_date is datetime
    if isinstance(due_date, str):
        due_date = pd.to_datetime(due_date)
    
    if pd.isna(due_date):
        return 0
    
    # Calculate difference
    days = (as_of - due_date).days
    return max(0, days)


def _fallback_risk_scoring(
    invoices_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    payments_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Fallback rule-based risk scoring when no ML model available.
    
    Uses a simple heuristic:
    - 40% weight on days overdue
    - 20% weight on invoice amount
    - 20% weight on payment terms
    - 20% weight on credit utilization
    """
    logger.info("Using fallback rule-based risk scoring...")
    
    df = invoices_df.copy()
    
    # Parse dates robustly - ALWAYS convert (don't check dtype)
    df["due_date"] = pd.to_datetime(df["due_date"], errors='coerce')
    
    # Calculate days overdue using vectorized operations
    now = pd.Timestamp.now()
    time_diff = now - df["due_date"]
    df["days_overdue_calc"] = time_diff.dt.days.fillna(0).clip(lower=0)
    
    # Component scores (0-100)
    # 1. Days overdue score (40% weight)
    df["overdue_score"] = (df["days_overdue_calc"] / 90 * 100).clip(0, 100)
    
    # 2. Invoice amount score (20% weight - normalize to 0-100)
    amount_max = df["invoice_amount"].quantile(0.95)
    if amount_max > 0:
        df["amount_score"] = (df["invoice_amount"] / amount_max * 100).clip(0, 100)
    else:
        df["amount_score"] = 0
    
    # 3. Payment terms score (20% weight)
    df = df.merge(
        customers_df[["customer_id", "payment_terms_days"]], 
        on="customer_id", 
        how="left"
    )
    df["payment_terms_days"] = df["payment_terms_days"].fillna(30)
    df["terms_score"] = (df["payment_terms_days"] / 60 * 100).clip(0, 100)
    
    # 4. Credit utilization score (20% weight)
    df = df.merge(
        customers_df[["customer_id", "credit_limit"]], 
        on="customer_id", 
        how="left"
    )
    
    # Calculate total outstanding per customer
    customer_totals = df.groupby("customer_id")["invoice_amount"].sum().reset_index()
    customer_totals.columns = ["customer_id", "total_outstanding"]
    df = df.merge(customer_totals, on="customer_id", how="left")
    
    # Calculate utilization
    df["credit_limit"] = df["credit_limit"].fillna(999999)
    df["utilization"] = (df["total_outstanding"] / df["credit_limit"] * 100).clip(0, 100)
    df["utilization_score"] = df["utilization"]
    
    # Combine scores with weights
    df["risk_score"] = (
        df["overdue_score"] * 0.40 +
        df["amount_score"] * 0.20 +
        df["terms_score"] * 0.20 +
        df["utilization_score"] * 0.20
    ).round(0).astype(int)
    
    # Categorize
    df["risk_category"] = df["risk_score"].apply(_categorize_risk)
    
    # Filter to open invoices only
    df = df[df["status"] == "open"].copy()
    
    # Select output columns (only those that exist)
    base_cols = [
        "invoice_id", "customer_id", "issue_date", "due_date",
        "invoice_amount", "currency", "status"
    ]
    score_cols = ["risk_score", "risk_category"]
    
    output_cols = [col for col in base_cols + score_cols if col in df.columns]
    result = df[output_cols].copy()
    
    # Sort by risk score descending
    result = result.sort_values("risk_score", ascending=False)
    
    logger.info(f"✓ Fallback scoring complete - scored {len(result)} open invoices")
    
    return result


def predict_payment_date(
    invoice_df: pd.DataFrame,
    customer_df: pd.DataFrame,
    model: LatePaymentModel
) -> pd.Series:
    """
    Predict expected payment date for an invoice.
    
    Args:
        invoice_df: Single invoice row as DataFrame
        customer_df: Customer information
        model: Trained prediction model
        
    Returns:
        Predicted payment date
    """
    # Get late payment probability
    late_prob = model.predict_proba(invoice_df)[0]
    
    # Estimate delay based on probability
    # High probability -> longer delay
    estimated_delay_days = int(late_prob * 45)  # Max 45 days delay
    
    # Add to due date
    due_date = pd.to_datetime(invoice_df["due_date"].iloc[0])
    predicted_date = due_date + pd.Timedelta(days=estimated_delay_days)
    
    return predicted_date