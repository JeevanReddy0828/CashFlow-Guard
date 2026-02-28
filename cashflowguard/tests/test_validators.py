"""Tests for data validators."""

import pandas as pd
import pytest
from datetime import datetime

from cashflowguard.io.validators import validate_customers, validate_invoices


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
