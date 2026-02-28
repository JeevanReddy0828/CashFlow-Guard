"""Configuration management for CashFlowGuard."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Global configuration for CashFlowGuard."""
    
    # Paths
    data_dir: Path = Field(default=Path("data/sample"))
    output_dir: Path = Field(default=Path("outputs"))
    model_dir: Path = Field(default=Path("models"))
    template_dir: Path = Field(default=Path("cashflowguard/templates"))
    
    # Analysis parameters
    late_payment_threshold_days: int = Field(default=7, ge=0)
    high_risk_threshold: int = Field(default=70, ge=0, le=100)
    min_invoice_amount: float = Field(default=0.0, ge=0.0)
    
    # ML parameters
    test_size: float = Field(default=0.25, ge=0.1, le=0.5)
    random_seed: int = Field(default=42)
    cv_folds: int = Field(default=5, ge=2)
    
    # Model hyperparameters
    model_type: Literal["logistic", "gradient_boost", "ensemble"] = "gradient_boost"
    max_depth: int = Field(default=5, ge=2, le=10)
    n_estimators: int = Field(default=100, ge=10, le=500)
    learning_rate: float = Field(default=0.1, ge=0.01, le=1.0)
    
    # Collections parameters
    max_reminders: int = Field(default=5, ge=1)
    escalation_days: list[int] = Field(default=[3, 10, 20, 45, 90])
    
    # Output formats
    output_format: Literal["text", "json", "html", "all"] = "all"
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True
    
    def ensure_directories(self) -> None:
        """Create all required directories."""
        for dir_path in [self.output_dir, self.model_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.output_dir / "messages").mkdir(exist_ok=True)
        (self.output_dir / "reports").mkdir(exist_ok=True)
        (self.output_dir / "plans").mkdir(exist_ok=True)


# Default configuration instance
default_config = Config()
