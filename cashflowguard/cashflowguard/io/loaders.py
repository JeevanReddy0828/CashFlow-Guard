"""Data loading utilities for CashFlowGuard."""

from pathlib import Path
from typing import Optional

import pandas as pd

from cashflowguard.io.validators import validate_all
from cashflowguard.utils import logger


class DataLoader:
    """Load and validate CashFlowGuard data files."""
    
    def __init__(self, data_dir: Path):
        """
        Initialize data loader.
        
        Args:
            data_dir: Directory containing CSV files
        """
        self.data_dir = Path(data_dir)
        
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")
    
    def load_customers(self) -> pd.DataFrame:
        """
        Load customers.csv.
        
        Returns:
            Customers DataFrame
            
        Raises:
            FileNotFoundError: If customers.csv not found
        """
        filepath = self.data_dir / "customers.csv"
        
        if not filepath.exists():
            raise FileNotFoundError(f"customers.csv not found in {self.data_dir}")
        
        logger.info(f"Loading {filepath}")
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} customers")
        
        return df
    
    def load_invoices(self) -> pd.DataFrame:
        """
        Load invoices.csv.
        
        Returns:
            Invoices DataFrame
            
        Raises:
            FileNotFoundError: If invoices.csv not found
        """
        filepath = self.data_dir / "invoices.csv"
        
        if not filepath.exists():
            raise FileNotFoundError(f"invoices.csv not found in {self.data_dir}")
        
        logger.info(f"Loading {filepath}")
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} invoices")
        
        return df
    
    def load_payments(self) -> Optional[pd.DataFrame]:
        """
        Load payments.csv if it exists.
        
        Returns:
            Payments DataFrame or None if file doesn't exist
        """
        filepath = self.data_dir / "payments.csv"
        
        if not filepath.exists():
            logger.warning(f"payments.csv not found in {self.data_dir} - will use fallback")
            return None
        
        logger.info(f"Loading {filepath}")
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} payments")
        
        return df
    
    def load_actions(self) -> pd.DataFrame:
        """
        Load actions.csv if it exists, otherwise return empty DataFrame.
        
        Returns:
            Actions DataFrame
        """
        filepath = self.data_dir / "actions.csv"
        
        if not filepath.exists():
            logger.info("actions.csv not found - returning empty DataFrame")
            return pd.DataFrame(columns=[
                "action_id", "invoice_id", "action_type",
                "action_date", "notes", "outcome"
            ])
        
        logger.info(f"Loading {filepath}")
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} actions")
        
        return df
    
    def load_all(
        self,
        validate: bool = True
    ) -> tuple[pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame], pd.DataFrame]:
        """
        Load all data files.
        
        Args:
            validate: Whether to validate data after loading
            
        Returns:
            Tuple of (customers, invoices, payments, actions)
            
        Raises:
            ValueError: If validation fails
        """
        customers_df = self.load_customers()
        invoices_df = self.load_invoices()
        payments_df = self.load_payments()
        actions_df = self.load_actions()
        
        if validate:
            if not validate_all(customers_df, invoices_df, payments_df):
                raise ValueError("Data validation failed - fix errors and try again")
        
        return customers_df, invoices_df, payments_df, actions_df


def save_actions(actions_df: pd.DataFrame, data_dir: Path) -> None:
    """
    Save actions DataFrame to CSV.
    
    Args:
        actions_df: Actions DataFrame
        data_dir: Directory to save to
    """
    filepath = data_dir / "actions.csv"
    actions_df.to_csv(filepath, index=False)
    logger.info(f"Saved {len(actions_df)} actions to {filepath}")


def save_dataframe(
    df: pd.DataFrame,
    filepath: Path,
    description: str = "data"
) -> None:
    """
    Save DataFrame to CSV.
    
    Args:
        df: DataFrame to save
        filepath: Output file path
        description: Description for logging
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=False)
    logger.info(f"Saved {description} to {filepath}")
