"""Model training for late payment prediction."""

import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

from cashflowguard.ml.features import (
    create_target_variable,
    engineer_features,
    get_feature_columns,
)
from cashflowguard.utils import logger, parse_date


class LatePaymentModel:
    """Late payment prediction model."""
    
    def __init__(
        self,
        model_type: str = "gradient_boost",
        random_seed: int = 42,
        **model_params
    ):
        """
        Initialize model.
        
        Args:
            model_type: Type of model ('logistic', 'gradient_boost')
            random_seed: Random seed for reproducibility
            **model_params: Additional model hyperparameters
        """
        self.model_type = model_type
        self.random_seed = random_seed
        self.model_params = model_params
        
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = get_feature_columns()
        self.feature_importances_ = None
        self.is_trained = False
        
        self._initialize_model()
    
    def _initialize_model(self) -> None:
        """Initialize the underlying model."""
        if self.model_type == "logistic":
            self.model = LogisticRegression(
                random_state=self.random_seed,
                max_iter=1000,
                **self.model_params
            )
        elif self.model_type == "gradient_boost":
            default_params = {
                "n_estimators": 100,
                "max_depth": 5,
                "learning_rate": 0.1,
                "min_samples_split": 20,
                "min_samples_leaf": 10,
                "subsample": 0.8,
                "random_state": self.random_seed
            }
            default_params.update(self.model_params)
            self.model = GradientBoostingClassifier(**default_params)
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def train(
        self,
        invoices_df: pd.DataFrame,
        customers_df: pd.DataFrame,
        payments_df: pd.DataFrame,
        late_threshold_days: int = 7,
        test_size: float = 0.25,
        cv_folds: int = 5
    ) -> dict[str, any]:
        """
        Train the model.
        
        Args:
            invoices_df: Invoices DataFrame
            customers_df: Customers DataFrame
            payments_df: Payments DataFrame
            late_threshold_days: Threshold for late payment
            test_size: Test set proportion
            cv_folds: Cross-validation folds
            
        Returns:
            Dictionary with training metrics
        """
        logger.info(f"Training {self.model_type} model...")
        
        # Create target variable
        logger.info("Creating target variable...")
        df = create_target_variable(invoices_df, payments_df, late_threshold_days)
        
        # Filter to paid invoices only (need labels)
        df = df[df["is_late"].notna()]
        
        if len(df) < 50:
            raise ValueError(
                f"Insufficient training data: {len(df)} paid invoices. "
                "Need at least 50 for reliable training."
            )
        
        logger.info(f"Training on {len(df)} paid invoices")
        logger.info(f"Late payment rate: {df['is_late'].mean() * 100:.2f}%")
        
        # Engineer features
        logger.info("Engineering features...")
        
        # Use issue_date as as_of for historical simulation
        feature_df = engineer_features(
            df,
            customers_df,
            payments_df,
            as_of=None  # Will use current time, but we filter to historical only
        )
        
        # Get features and target
        X = feature_df[self.feature_columns]
        y = feature_df["is_late"]
        
        # Handle missing values
        X = X.fillna(0)
        
        # Time-based split (train on older, test on newer)
        logger.info("Creating time-based train/test split...")
        df_sorted = feature_df.sort_values("issue_date")
        split_idx = int(len(df_sorted) * (1 - test_size))
        
        train_df = df_sorted.iloc[:split_idx]
        test_df = df_sorted.iloc[split_idx:]
        
        X_train = train_df[self.feature_columns].fillna(0)
        y_train = train_df["is_late"]
        X_test = test_df[self.feature_columns].fillna(0)
        y_test = test_df["is_late"]
        
        logger.info(f"Train set: {len(X_train)} samples")
        logger.info(f"Test set: {len(X_test)} samples")
        
        # Scale features
        logger.info("Scaling features...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Cross-validation
        logger.info(f"Running {cv_folds}-fold cross-validation...")
        cv_scores = cross_val_score(
            self.model,
            X_train_scaled,
            y_train,
            cv=StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=self.random_seed),
            scoring="roc_auc",
            n_jobs=-1
        )
        
        logger.info(f"CV ROC-AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
        
        # Train final model
        logger.info("Training final model...")
        self.model.fit(X_train_scaled, y_train)
        
        # Get feature importances
        if hasattr(self.model, "feature_importances_"):
            self.feature_importances_ = pd.DataFrame({
                "feature": self.feature_columns,
                "importance": self.model.feature_importances_
            }).sort_values("importance", ascending=False)
        
        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        self.is_trained = True
        
        metrics = {
            "model_type": self.model_type,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "train_accuracy": round(train_score, 4),
            "test_accuracy": round(test_score, 4),
            "cv_roc_auc_mean": round(cv_scores.mean(), 4),
            "cv_roc_auc_std": round(cv_scores.std(), 4),
            "late_rate": round(y.mean() * 100, 2),
            "late_threshold_days": late_threshold_days,
            "trained_at": datetime.now().isoformat(),
        }
        
        logger.info("✓ Model training complete")
        logger.info(f"  Train accuracy: {metrics['train_accuracy']:.4f}")
        logger.info(f"  Test accuracy: {metrics['test_accuracy']:.4f}")
        logger.info(f"  CV ROC-AUC: {metrics['cv_roc_auc_mean']:.4f}")
        
        return metrics
    
    def predict_proba(
        self,
        invoices_df: pd.DataFrame,
        customers_df: pd.DataFrame,
        payments_df: Optional[pd.DataFrame] = None
    ) -> np.ndarray:
        """
        Predict late payment probabilities.
        
        Args:
            invoices_df: Invoices DataFrame
            customers_df: Customers DataFrame
            payments_df: Payments DataFrame (for customer history)
            
        Returns:
            Array of probabilities (shape: n_samples x 2)
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first.")
        
        # Engineer features
        feature_df = engineer_features(
            invoices_df,
            customers_df,
            payments_df
        )
        
        # Get features
        X = feature_df[self.feature_columns].fillna(0)
        
        # Scale
        X_scaled = self.scaler.transform(X)
        
        # Predict
        probas = self.model.predict_proba(X_scaled)
        
        return probas
    
    def predict_risk_scores(
        self,
        invoices_df: pd.DataFrame,
        customers_df: pd.DataFrame,
        payments_df: Optional[pd.DataFrame] = None
    ) -> pd.Series:
        """
        Predict risk scores (0-100).
        
        Args:
            invoices_df: Invoices DataFrame
            customers_df: Customers DataFrame
            payments_df: Payments DataFrame
            
        Returns:
            Series of risk scores
        """
        probas = self.predict_proba(invoices_df, customers_df, payments_df)
        
        # Convert to risk score (0-100)
        risk_scores = (probas[:, 1] * 100).round(2)
        
        return pd.Series(risk_scores, index=invoices_df.index)
    
    def save(self, filepath: Path) -> None:
        """
        Save model to disk.
        
        Args:
            filepath: Path to save model
        """
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_columns": self.feature_columns,
            "model_type": self.model_type,
            "random_seed": self.random_seed,
            "model_params": self.model_params,
            "feature_importances": self.feature_importances_,
        }
        
        with open(filepath, "wb") as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: Path) -> "LatePaymentModel":
        """
        Load model from disk.
        
        Args:
            filepath: Path to load model from
            
        Returns:
            Loaded model instance
        """
        with open(filepath, "rb") as f:
            model_data = pickle.load(f)
        
        # Create instance
        instance = cls(
            model_type=model_data["model_type"],
            random_seed=model_data["random_seed"],
            **model_data["model_params"]
        )
        
        # Restore state
        instance.model = model_data["model"]
        instance.scaler = model_data["scaler"]
        instance.feature_columns = model_data["feature_columns"]
        instance.feature_importances_ = model_data["feature_importances"]
        instance.is_trained = True
        
        logger.info(f"Model loaded from {filepath}")
        
        return instance


def train_model(
    invoices_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    model_type: str = "gradient_boost",
    late_threshold_days: int = 7,
    test_size: float = 0.25,
    random_seed: int = 42,
    **model_params
) -> tuple[LatePaymentModel, dict]:
    """
    Train a late payment prediction model.
    
    Args:
        invoices_df: Invoices DataFrame
        customers_df: Customers DataFrame
        payments_df: Payments DataFrame
        model_type: Type of model to train
        late_threshold_days: Threshold for late payment
        test_size: Test set proportion
        random_seed: Random seed
        **model_params: Model hyperparameters
        
    Returns:
        Tuple of (trained model, metrics dictionary)
    """
    model = LatePaymentModel(
        model_type=model_type,
        random_seed=random_seed,
        **model_params
    )
    
    metrics = model.train(
        invoices_df,
        customers_df,
        payments_df,
        late_threshold_days=late_threshold_days,
        test_size=test_size
    )
    
    return model, metrics
