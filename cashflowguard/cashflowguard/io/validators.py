"""Data validation for CashFlowGuard CSV files."""

from datetime import datetime
from enum import Enum
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from cashflowguard.utils import logger, parse_date


class InvoiceStatus(str, Enum):
    """Valid invoice statuses."""
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    CANCELLED = "cancelled"


class InvoiceType(str, Enum):
    """Valid invoice types."""
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    MILESTONE = "milestone"
    RETAINER = "retainer"


class Channel(str, Enum):
    """Valid sales channels."""
    ONLINE = "online"
    OFFLINE = "offline"
    BOTH = "both"


class PaymentMethod(str, Enum):
    """Valid payment methods."""
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    CHECK = "check"
    CASH = "cash"
    WIRE = "wire"
    ACH = "ach"
    OTHER = "other"


class PaymentStatus(str, Enum):
    """Valid payment statuses."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class ActionType(str, Enum):
    """Valid collection action types."""
    REMINDER1 = "reminder1"
    REMINDER2 = "reminder2"
    REMINDER3 = "reminder3"
    CALL = "call"
    EMAIL_FRIENDLY = "email_friendly"
    EMAIL_FIRM = "email_firm"
    EMAIL_FINAL = "email_final"
    PAYMENT_PLAN = "payment_plan"
    PAUSE_SERVICE = "pause_service"
    ESCALATE = "escalate"
    LEGAL = "legal"


class ActionOutcome(str, Enum):
    """Valid action outcomes."""
    PENDING = "pending"
    SUCCESS = "success"
    NO_RESPONSE = "no_response"
    DISPUTE = "dispute"
    PROMISE_TO_PAY = "promise_to_pay"
    PAYMENT_PLAN_ACCEPTED = "payment_plan_accepted"


class Customer(BaseModel):
    """Customer data model."""
    customer_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    phone: Optional[str] = Field(None, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    country: str = Field(..., min_length=2, max_length=2)
    state: Optional[str] = Field(default=None, max_length=50)
    payment_terms_days: int = Field(..., ge=0, le=365)
    credit_limit: float = Field(..., ge=0)
    created_at: datetime
    
    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v: str | datetime) -> datetime:
        """Parse created_at date."""
        if isinstance(v, datetime):
            return v
        return parse_date(v)
    
    class Config:
        """Pydantic config."""
        str_strip_whitespace = True


class Invoice(BaseModel):
    """Invoice data model."""
    invoice_id: str = Field(..., min_length=1, max_length=100)
    customer_id: str = Field(..., min_length=1, max_length=100)
    issue_date: datetime
    due_date: datetime
    invoice_amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: InvoiceStatus
    invoice_type: InvoiceType
    channel: Channel
    created_at: datetime
    
    @field_validator("issue_date", "due_date", "created_at", mode="before")
    @classmethod
    def parse_dates(cls, v: str | datetime) -> datetime:
        """Parse date fields."""
        if isinstance(v, datetime):
            return v
        return parse_date(v)
    
    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, v: str) -> str:
        """Normalize status."""
        return v.lower().strip()
    
    @field_validator("invoice_type", mode="before")
    @classmethod
    def parse_invoice_type(cls, v: str) -> str:
        """Normalize invoice type."""
        return v.lower().strip()
    
    @field_validator("channel", mode="before")
    @classmethod
    def parse_channel(cls, v: str) -> str:
        """Normalize channel."""
        return v.lower().strip()
    
    class Config:
        """Pydantic config."""
        str_strip_whitespace = True


class Payment(BaseModel):
    """Payment data model."""
    payment_id: str = Field(..., min_length=1, max_length=100)
    invoice_id: str = Field(..., min_length=1, max_length=100)
    payment_date: datetime
    amount: float = Field(..., gt=0)
    method: PaymentMethod
    status: PaymentStatus
    
    @field_validator("payment_date", mode="before")
    @classmethod
    def parse_payment_date(cls, v: str | datetime) -> datetime:
        """Parse payment date."""
        if isinstance(v, datetime):
            return v
        return parse_date(v)
    
    @field_validator("method", mode="before")
    @classmethod
    def parse_method(cls, v: str) -> str:
        """Normalize payment method."""
        return v.lower().strip()
    
    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, v: str) -> str:
        """Normalize status."""
        return v.lower().strip()
    
    class Config:
        """Pydantic config."""
        str_strip_whitespace = True


class Action(BaseModel):
    """Collection action data model."""
    action_id: str = Field(..., min_length=1, max_length=100)
    invoice_id: str = Field(..., min_length=1, max_length=100)
    action_type: ActionType
    action_date: datetime
    notes: Optional[str] = Field(None, max_length=1000)
    outcome: ActionOutcome
    
    @field_validator("action_date", mode="before")
    @classmethod
    def parse_action_date(cls, v: str | datetime) -> datetime:
        """Parse action date."""
        if isinstance(v, datetime):
            return v
        return parse_date(v)
    
    @field_validator("action_type", mode="before")
    @classmethod
    def parse_action_type(cls, v: str) -> str:
        """Normalize action type."""
        return v.lower().strip()
    
    @field_validator("outcome", mode="before")
    @classmethod
    def parse_outcome(cls, v: str) -> str:
        """Normalize outcome."""
        return v.lower().strip()
    
    class Config:
        """Pydantic config."""
        str_strip_whitespace = True


class ValidationResult(BaseModel):
    """Validation result model."""
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    row_count: int = 0
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.is_valid = False
        self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
    
    def print_summary(self) -> None:
        """Print validation summary."""
        if self.is_valid:
            logger.info(f"✓ Validation passed ({self.row_count} rows)")
            if self.warnings:
                for warning in self.warnings:
                    logger.warning(f"⚠ {warning}")
        else:
            logger.error(f"✗ Validation failed ({len(self.errors)} errors)")
            for error in self.errors:
                logger.error(f"  • {error}")


def validate_customers(df: pd.DataFrame) -> ValidationResult:
    """
    Validate customers DataFrame.
    
    Args:
        df: Customers DataFrame
        
    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(is_valid=True, row_count=len(df))
    
    # Check required columns
    required_cols = [
        "customer_id", "name", "email", "country",
        "payment_terms_days", "credit_limit", "created_at"
    ]
    
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        result.add_error(f"Missing required columns: {missing_cols}")
        return result
    
    # Check for duplicates
    if df["customer_id"].duplicated().any():
        dupes = df[df["customer_id"].duplicated(keep=False)]["customer_id"].unique()
        result.add_error(f"Duplicate customer_ids found: {list(dupes)}")
    
    # Validate each row
    for idx, row in df.iterrows():
        try:
            # Convert NaN to None for optional fields
            row_dict = row.to_dict()
            for key in ["phone", "industry", "state"]:
                if pd.isna(row_dict.get(key)):
                    row_dict[key] = None
            Customer(**row_dict)
        except Exception as e:
            result.add_error(f"Row {idx}: {str(e)}")
    
    # Warnings
    if df["email"].isna().any():
        result.add_warning(f"{df['email'].isna().sum()} customers missing email")
    
    if df["phone"].isna().any():
        result.add_warning(f"{df['phone'].isna().sum()} customers missing phone")
    
    return result


def validate_invoices(df: pd.DataFrame, customers_df: pd.DataFrame) -> ValidationResult:
    """
    Validate invoices DataFrame.
    
    Args:
        df: Invoices DataFrame
        customers_df: Customers DataFrame for foreign key validation
        
    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(is_valid=True, row_count=len(df))
    
    # Check required columns
    required_cols = [
        "invoice_id", "customer_id", "issue_date", "due_date",
        "invoice_amount", "currency", "status", "invoice_type",
        "channel", "created_at"
    ]
    
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        result.add_error(f"Missing required columns: {missing_cols}")
        return result
    
    # Check for duplicates
    if df["invoice_id"].duplicated().any():
        dupes = df[df["invoice_id"].duplicated(keep=False)]["invoice_id"].unique()
        result.add_error(f"Duplicate invoice_ids found: {list(dupes)}")
    
    # Foreign key check
    valid_customers = set(customers_df["customer_id"])
    invalid_customers = set(df["customer_id"]) - valid_customers
    if invalid_customers:
        result.add_error(
            f"Invoices reference non-existent customers: {list(invalid_customers)[:5]}"
        )
    
    # Validate each row
    for idx, row in df.iterrows():
        try:
            invoice = Invoice(**row.to_dict())
            
            # Business logic validation
            if invoice.due_date < invoice.issue_date:
                result.add_error(f"Invoice {invoice.invoice_id}: due_date before issue_date")
            
            if invoice.created_at < invoice.issue_date:
                result.add_warning(
                    f"Invoice {invoice.invoice_id}: created_at before issue_date"
                )
                
        except Exception as e:
            result.add_error(f"Row {idx} ({row.get('invoice_id', 'unknown')}): {str(e)}")
    
    return result


def validate_payments(
    df: pd.DataFrame,
    invoices_df: pd.DataFrame
) -> ValidationResult:
    """
    Validate payments DataFrame.
    
    Args:
        df: Payments DataFrame
        invoices_df: Invoices DataFrame for foreign key validation
        
    Returns:
        ValidationResult with errors and warnings
    """
    result = ValidationResult(is_valid=True, row_count=len(df))
    
    # Check required columns
    required_cols = [
        "payment_id", "invoice_id", "payment_date",
        "amount", "method", "status"
    ]
    
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        result.add_error(f"Missing required columns: {missing_cols}")
        return result
    
    # Check for duplicates
    if df["payment_id"].duplicated().any():
        dupes = df[df["payment_id"].duplicated(keep=False)]["payment_id"].unique()
        result.add_error(f"Duplicate payment_ids found: {list(dupes)}")
    
    # Foreign key check
    valid_invoices = set(invoices_df["invoice_id"])
    invalid_invoices = set(df["invoice_id"]) - valid_invoices
    if invalid_invoices:
        result.add_error(
            f"Payments reference non-existent invoices: {list(invalid_invoices)[:5]}"
        )
    
    # Validate each row
    for idx, row in df.iterrows():
        try:
            Payment(**row.to_dict())
        except Exception as e:
            result.add_error(f"Row {idx} ({row.get('payment_id', 'unknown')}): {str(e)}")
    
    # Check for overpayments
    invoice_payments = df.groupby("invoice_id")["amount"].sum()
    invoice_amounts = invoices_df.set_index("invoice_id")["invoice_amount"]
    
    for invoice_id, paid_amount in invoice_payments.items():
        if invoice_id in invoice_amounts.index:
            invoice_amount = invoice_amounts[invoice_id]
            if paid_amount > invoice_amount * 1.01:  # Allow 1% tolerance
                result.add_warning(
                    f"Invoice {invoice_id}: payments (${paid_amount:.2f}) "
                    f"exceed invoice amount (${invoice_amount:.2f})"
                )
    
    return result


def validate_all(
    customers_df: pd.DataFrame,
    invoices_df: pd.DataFrame,
    payments_df: Optional[pd.DataFrame] = None,
) -> bool:
    """
    Validate all data files.
    
    Args:
        customers_df: Customers DataFrame
        invoices_df: Invoices DataFrame
        payments_df: Optional payments DataFrame
        
    Returns:
        True if all validations pass, False otherwise
    """
    logger.info("Validating data files...")
    
    # Validate customers
    logger.info("Validating customers.csv...")
    customers_result = validate_customers(customers_df)
    customers_result.print_summary()
    
    # Validate invoices
    logger.info("Validating invoices.csv...")
    invoices_result = validate_invoices(invoices_df, customers_df)
    invoices_result.print_summary()
    
    # Validate payments if provided
    payments_valid = True
    if payments_df is not None and not payments_df.empty:
        logger.info("Validating payments.csv...")
        payments_result = validate_payments(payments_df, invoices_df)
        payments_result.print_summary()
        payments_valid = payments_result.is_valid
    
    all_valid = customers_result.is_valid and invoices_result.is_valid and payments_valid
    
    if all_valid:
        logger.info("✓ All validations passed")
    else:
        logger.error("✗ Validation failed - please fix errors above")
    
    return all_valid
