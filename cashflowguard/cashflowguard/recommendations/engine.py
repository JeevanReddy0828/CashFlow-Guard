"""Collections recommendations engine."""

from datetime import datetime
from typing import Optional

import pandas as pd

from cashflowguard.utils import days_overdue, logger


class RecommendationEngine:
    """Engine for generating collection action recommendations."""
    
    def __init__(
        self,
        high_value_threshold: float = 10000,
        max_reminders: int = 5
    ):
        """
        Initialize recommendation engine.
        
        Args:
            high_value_threshold: Threshold for high-value customers
            max_reminders: Maximum number of reminders to send
        """
        self.high_value_threshold = high_value_threshold
        self.max_reminders = max_reminders
    
    def recommend_actions(
        self,
        invoices_df: pd.DataFrame,
        customers_df: pd.DataFrame,
        actions_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Recommend collection actions for open invoices.
        
        Args:
            invoices_df: Invoices DataFrame (must have risk_score column)
            customers_df: Customers DataFrame
            actions_df: Actions DataFrame (to check prior outreach)
            
        Returns:
            DataFrame with recommended actions
        """
        # Filter to open invoices
        df = invoices_df[invoices_df["status"] == "open"].copy()
        
        if len(df) == 0:
            logger.info("No open invoices - no actions to recommend")
            return pd.DataFrame()
        
        logger.info(f"Generating recommendations for {len(df)} open invoices...")
        
        # Calculate days overdue
        df["days_overdue"] = df["due_date"].apply(days_overdue)
        
        # Merge customer info
        df = df.merge(
            customers_df[["customer_id", "name"]],
            on="customer_id",
            how="left"
        )
        
        # Count prior actions if available
        if actions_df is not None and not actions_df.empty:
            action_counts = actions_df.groupby("invoice_id").size().rename("prior_actions")
            df = df.merge(action_counts, left_on="invoice_id", right_index=True, how="left")
            df["prior_actions"] = df["prior_actions"].fillna(0).astype(int)
        else:
            df["prior_actions"] = 0
        
        # Determine customer tier
        df["is_high_value"] = df["invoice_amount"] >= self.high_value_threshold
        
        # Generate recommendations
        df["recommended_action"] = df.apply(self._determine_action, axis=1)
        df["action_priority"] = df.apply(self._calculate_priority, axis=1)
        df["urgency"] = df.apply(self._determine_urgency, axis=1)
        df["message_tone"] = df.apply(self._determine_tone, axis=1)
        
        # Sort by priority
        df = df.sort_values("action_priority", ascending=False)
        
        logger.info("✓ Recommendations generated")
        
        return df
    
    def _determine_action(self, row: pd.Series) -> str:
        """Determine recommended action based on invoice characteristics."""
        days_overdue = row["days_overdue"]
        risk_score = row.get("risk_score", 50)
        prior_actions = row["prior_actions"]
        is_high_value = row["is_high_value"]
        
        # Exceeded max reminders -> escalate
        if prior_actions >= self.max_reminders:
            return "escalate"
        
        # Not yet overdue but high risk -> proactive
        if days_overdue <= 0 and risk_score >= 70:
            return "friendly_reminder"
        
        # 0-3 days overdue
        if 0 < days_overdue <= 3:
            if prior_actions == 0:
                return "friendly_reminder"
            else:
                return "second_reminder"
        
        # 4-10 days overdue
        elif 4 <= days_overdue <= 10:
            if prior_actions == 0:
                return "reminder_with_inquiry"
            else:
                return "call"
        
        # 11-20 days overdue
        elif 11 <= days_overdue <= 20:
            if is_high_value:
                return "call"
            else:
                return "firm_reminder"
        
        # 21-45 days overdue
        elif 21 <= days_overdue <= 45:
            if prior_actions < 2:
                return "payment_plan_offer"
            else:
                return "pause_service_warning"
        
        # 45+ days overdue
        else:
            if is_high_value:
                return "escalate"
            else:
                return "final_notice"
    
    def _calculate_priority(self, row: pd.Series) -> int:
        """
        Calculate action priority score (0-100, higher = more urgent).
        
        Factors:
        - Days overdue (40%)
        - Risk score (30%)
        - Invoice amount (20%)
        - Prior actions (10%)
        """
        days_overdue = row["days_overdue"]
        risk_score = row.get("risk_score", 50)
        amount = row["invoice_amount"]
        prior_actions = row["prior_actions"]
        
        # Days overdue score
        overdue_score = min(100, (days_overdue / 90) * 100)
        
        # Amount score (normalized to 0-100)
        amount_score = min(100, (amount / 50000) * 100)
        
        # Prior actions score (more actions = more urgent)
        actions_score = min(100, (prior_actions / 5) * 100)
        
        # Weighted priority
        priority = (
            overdue_score * 0.4 +
            risk_score * 0.3 +
            amount_score * 0.2 +
            actions_score * 0.1
        )
        
        return int(priority)
    
    def _determine_urgency(self, row: pd.Series) -> str:
        """Determine urgency level."""
        priority = row["action_priority"]
        
        if priority >= 75:
            return "critical"
        elif priority >= 50:
            return "high"
        elif priority >= 25:
            return "medium"
        else:
            return "low"
    
    def _determine_tone(self, row: pd.Series) -> str:
        """Determine message tone."""
        days_overdue = row["days_overdue"]
        prior_actions = row["prior_actions"]
        is_high_value = row["is_high_value"]
        
        # High value customers get friendlier tone
        if is_high_value and days_overdue < 15:
            return "friendly"
        
        # Few days overdue, first contact
        if days_overdue <= 7 and prior_actions == 0:
            return "friendly"
        
        # Multiple attempts or significantly overdue
        if prior_actions >= 2 or days_overdue >= 30:
            return "firm"
        
        # Default
        return "neutral"
    
    def get_top_recommendations(
        self,
        recommendations_df: pd.DataFrame,
        top_n: int = 30,
        min_priority: int = 0
    ) -> pd.DataFrame:
        """
        Get top N recommendations by priority.
        
        Args:
            recommendations_df: Recommendations DataFrame
            top_n: Number of top recommendations to return
            min_priority: Minimum priority threshold
            
        Returns:
            Filtered DataFrame with top recommendations
        """
        df = recommendations_df[recommendations_df["action_priority"] >= min_priority]
        return df.head(top_n)
    
    def get_recommendations_by_week(
        self,
        recommendations_df: pd.DataFrame,
        week_date: str,
        top_n: int = 30
    ) -> pd.DataFrame:
        """
        Get recommendations for a specific week.
        
        For now, returns top N by priority.
        Could be extended to spread actions across the week.
        
        Args:
            recommendations_df: Recommendations DataFrame
            week_date: Week starting date (YYYY-MM-DD)
            top_n: Number of recommendations
            
        Returns:
            Filtered DataFrame
        """
        # For V1, just return top N
        # V2 could distribute actions across weekdays
        return self.get_top_recommendations(recommendations_df, top_n)


def generate_recommendations(
    invoices_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    actions_df: Optional[pd.DataFrame] = None,
    high_value_threshold: float = 10000,
    max_reminders: int = 5
) -> pd.DataFrame:
    """
    Generate collection action recommendations.
    
    Args:
        invoices_df: Invoices DataFrame
        customers_df: Customers DataFrame
        actions_df: Actions DataFrame
        high_value_threshold: Threshold for high-value customers
        max_reminders: Maximum reminders to send
        
    Returns:
        DataFrame with recommendations
    """
    engine = RecommendationEngine(
        high_value_threshold=high_value_threshold,
        max_reminders=max_reminders
    )
    
    return engine.recommend_actions(invoices_df, customers_df, actions_df)
