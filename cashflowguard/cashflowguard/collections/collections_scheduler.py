"""
Collections scheduler for automated follow-up cadence.

Generates optimal follow-up schedules based on:
- Risk level
- Days overdue
- Previous contact history
- Business rules (no weekends, holidays)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd


class CollectionsScheduler:
    """Generate and manage collections follow-up schedules."""
    
    # Standard follow-up cadences (days between actions)
    CADENCES = {
        "low_risk": [7, 14, 21, 30],           # Weekly for first month
        "medium_risk": [5, 10, 15, 22, 30],    # Bi-weekly acceleration
        "high_risk": [3, 7, 10, 14, 17, 21],   # Aggressive weekly
        "very_high_risk": [1, 3, 5, 7, 9, 12, 15]  # Daily then weekly
    }
    
    def __init__(self, business_days_only: bool = True):
        """
        Initialize scheduler.
        
        Args:
            business_days_only: Skip weekends in scheduling
        """
        self.business_days_only = business_days_only
        self.holidays = set()  # Can be populated with company holidays
    
    def add_holidays(self, holiday_dates: List[datetime]):
        """Add company holidays to avoid scheduling on these days."""
        self.holidays.update(holiday_dates)
    
    def generate_schedule(
        self,
        invoice_id: str,
        customer_id: str,
        risk_level: str,
        days_overdue: int,
        last_contact_date: datetime = None,
        max_attempts: int = None
    ) -> List[Dict]:
        """
        Generate complete follow-up schedule for an invoice.
        
        Args:
            invoice_id: Invoice identifier
            customer_id: Customer identifier
            risk_level: Risk category (low, medium, high, very_high)
            days_overdue: Current days overdue
            last_contact_date: Date of last contact (None = today)
            max_attempts: Maximum follow-up attempts (None = use default)
            
        Returns:
            List of scheduled actions with dates and types
        """
        if last_contact_date is None:
            last_contact_date = datetime.now()
        
        # Get cadence for risk level
        risk_key = f"{risk_level}_risk"
        cadence = self.CADENCES.get(risk_key, self.CADENCES["medium_risk"])
        
        if max_attempts:
            cadence = cadence[:max_attempts]
        
        schedule = []
        
        for attempt_num, days_offset in enumerate(cadence, start=1):
            scheduled_date = self._get_next_business_date(
                last_contact_date + timedelta(days=days_offset)
            )
            
            action_type = self._determine_action_type(
                attempt_num, 
                days_overdue + days_offset,
                risk_level
            )
            
            schedule.append({
                "invoice_id": invoice_id,
                "customer_id": customer_id,
                "attempt_number": attempt_num,
                "scheduled_date": scheduled_date,
                "action_type": action_type,
                "days_from_last_contact": days_offset,
                "estimated_days_overdue": days_overdue + days_offset,
                "status": "pending"
            })
        
        return schedule
    
    def get_todays_actions(self, schedule_df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter schedule to get actions due today.
        
        Args:
            schedule_df: DataFrame with scheduled actions
            
        Returns:
            DataFrame of actions due today
        """
        today = datetime.now().date()
        schedule_df["scheduled_date"] = pd.to_datetime(schedule_df["scheduled_date"])
        
        return schedule_df[
            (schedule_df["scheduled_date"].dt.date == today) &
            (schedule_df["status"] == "pending")
        ].copy()
    
    def get_this_weeks_actions(self, schedule_df: pd.DataFrame) -> pd.DataFrame:
        """
        Get all actions due this week.
        
        Args:
            schedule_df: DataFrame with scheduled actions
            
        Returns:
            DataFrame of this week's actions
        """
        today = datetime.now()
        week_end = today + timedelta(days=7)
        
        schedule_df["scheduled_date"] = pd.to_datetime(schedule_df["scheduled_date"])
        
        return schedule_df[
            (schedule_df["scheduled_date"] >= today) &
            (schedule_df["scheduled_date"] <= week_end) &
            (schedule_df["status"] == "pending")
        ].sort_values("scheduled_date").copy()
    
    def reschedule_action(
        self,
        schedule_df: pd.DataFrame,
        invoice_id: str,
        attempt_number: int,
        new_date: datetime,
        reason: str = None
    ) -> pd.DataFrame:
        """
        Reschedule a specific action.
        
        Args:
            schedule_df: DataFrame with scheduled actions
            invoice_id: Invoice to reschedule
            attempt_number: Which attempt to reschedule
            new_date: New scheduled date
            reason: Reason for rescheduling
            
        Returns:
            Updated schedule DataFrame
        """
        mask = (
            (schedule_df["invoice_id"] == invoice_id) &
            (schedule_df["attempt_number"] == attempt_number)
        )
        
        new_date = self._get_next_business_date(new_date)
        schedule_df.loc[mask, "scheduled_date"] = new_date
        
        if reason:
            schedule_df.loc[mask, "reschedule_reason"] = reason
        
        return schedule_df
    
    def mark_completed(
        self,
        schedule_df: pd.DataFrame,
        invoice_id: str,
        attempt_number: int,
        completed_date: datetime = None,
        notes: str = None
    ) -> pd.DataFrame:
        """
        Mark an action as completed.
        
        Args:
            schedule_df: DataFrame with scheduled actions
            invoice_id: Invoice ID
            attempt_number: Attempt number completed
            completed_date: When action was completed
            notes: Completion notes
            
        Returns:
            Updated schedule DataFrame
        """
        mask = (
            (schedule_df["invoice_id"] == invoice_id) &
            (schedule_df["attempt_number"] == attempt_number)
        )
        
        schedule_df.loc[mask, "status"] = "completed"
        schedule_df.loc[mask, "completed_date"] = completed_date or datetime.now()
        
        if notes:
            schedule_df.loc[mask, "completion_notes"] = notes
        
        return schedule_df
    
    def cancel_future_actions(
        self,
        schedule_df: pd.DataFrame,
        invoice_id: str,
        reason: str = "Payment received"
    ) -> pd.DataFrame:
        """
        Cancel all future actions for an invoice (e.g., after payment).
        
        Args:
            schedule_df: DataFrame with scheduled actions
            invoice_id: Invoice ID to cancel
            reason: Cancellation reason
            
        Returns:
            Updated schedule DataFrame
        """
        mask = (
            (schedule_df["invoice_id"] == invoice_id) &
            (schedule_df["status"] == "pending")
        )
        
        schedule_df.loc[mask, "status"] = "cancelled"
        schedule_df.loc[mask, "cancellation_reason"] = reason
        schedule_df.loc[mask, "cancelled_date"] = datetime.now()
        
        return schedule_df
    
    def generate_weekly_plan(
        self,
        invoices_df: pd.DataFrame,
        schedule_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Generate this week's collections plan.
        
        Args:
            invoices_df: Open invoices with risk scores
            schedule_df: Existing schedule (None = generate new)
            
        Returns:
            DataFrame with this week's prioritized actions
        """
        # If no schedule exists, generate one for all open invoices
        if schedule_df is None or schedule_df.empty:
            all_schedules = []
            
            for _, invoice in invoices_df.iterrows():
                schedule = self.generate_schedule(
                    invoice_id=invoice["invoice_id"],
                    customer_id=invoice["customer_id"],
                    risk_level=invoice.get("risk_category", "medium"),
                    days_overdue=invoice.get("days_overdue", 0)
                )
                all_schedules.extend(schedule)
            
            schedule_df = pd.DataFrame(all_schedules)
        
        # Get this week's actions
        weekly_actions = self.get_this_weeks_actions(schedule_df)
        
        # Merge with invoice details
        weekly_plan = weekly_actions.merge(
            invoices_df[[
                "invoice_id", "customer_id", "invoice_amount", 
                "due_date", "risk_score"
            ]],
            on="invoice_id",
            how="left"
        )
        
        # Calculate priority score (risk × amount)
        weekly_plan["priority_score"] = (
            weekly_plan["risk_score"] * weekly_plan["invoice_amount"]
        )
        
        # Sort by priority
        weekly_plan = weekly_plan.sort_values(
            ["scheduled_date", "priority_score"],
            ascending=[True, False]
        )
        
        return weekly_plan
    
    def get_cadence_summary(self) -> pd.DataFrame:
        """
        Get summary of all cadence rules.
        
        Returns:
            DataFrame summarizing cadence by risk level
        """
        summary = []
        
        for risk_level, days in self.CADENCES.items():
            summary.append({
                "risk_level": risk_level,
                "total_attempts": len(days),
                "cadence_days": ", ".join(map(str, days)),
                "total_duration_days": max(days) if days else 0
            })
        
        return pd.DataFrame(summary)
    
    def _get_next_business_date(self, date: datetime) -> datetime:
        """
        Get next valid business date (skip weekends/holidays).
        
        Args:
            date: Target date
            
        Returns:
            Next valid business date
        """
        if not self.business_days_only:
            return date
        
        # Skip weekends
        while date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            date += timedelta(days=1)
        
        # Skip holidays
        while date.date() in self.holidays:
            date += timedelta(days=1)
            # Check again for weekends
            while date.weekday() >= 5:
                date += timedelta(days=1)
        
        return date
    
    def _determine_action_type(
        self,
        attempt_number: int,
        days_overdue: int,
        risk_level: str
    ) -> str:
        """
        Determine action type based on attempt and context.
        
        Args:
            attempt_number: Which attempt in sequence
            days_overdue: Days past due at time of action
            risk_level: Risk category
            
        Returns:
            Action type string
        """
        # Escalation ladder
        if attempt_number == 1:
            return "friendly_reminder"
        elif attempt_number == 2:
            return "second_notice"
        elif attempt_number == 3:
            if risk_level == "very_high" or days_overdue > 30:
                return "call_request"
            else:
                return "second_notice"
        elif attempt_number == 4:
            if days_overdue > 45:
                return "escalate"
            else:
                return "call_request"
        elif attempt_number >= 5:
            if days_overdue > 60:
                return "escalate"
            elif attempt_number % 2 == 0:
                return "payment_plan"
            else:
                return "call_request"
        
        return "friendly_reminder"
    
    def analyze_schedule_effectiveness(
        self,
        schedule_df: pd.DataFrame,
        payments_df: pd.DataFrame = None
    ) -> Dict:
        """
        Analyze effectiveness of scheduling strategy.
        
        Args:
            schedule_df: Completed schedule history
            payments_df: Payment records
            
        Returns:
            Dictionary with effectiveness metrics
        """
        if schedule_df.empty:
            return {
                "total_actions": 0,
                "completed_actions": 0,
                "completion_rate": 0,
                "avg_attempts_to_payment": 0
            }
        
        total_actions = len(schedule_df)
        completed = schedule_df[schedule_df["status"] == "completed"]
        completed_count = len(completed)
        
        metrics = {
            "total_actions": total_actions,
            "completed_actions": completed_count,
            "completion_rate": completed_count / total_actions if total_actions > 0 else 0,
            "cancelled_actions": len(schedule_df[schedule_df["status"] == "cancelled"]),
            "pending_actions": len(schedule_df[schedule_df["status"] == "pending"])
        }
        
        # Action type effectiveness
        if not completed.empty:
            action_effectiveness = completed.groupby("action_type").size().to_dict()
            metrics["action_type_distribution"] = action_effectiveness
        
        # Average attempts to success
        if payments_df is not None and not payments_df.empty:
            # Merge with payments to see which invoices got paid
            paid_invoices = schedule_df.merge(
                payments_df[["invoice_id"]].drop_duplicates(),
                on="invoice_id",
                how="inner"
            )
            
            if not paid_invoices.empty:
                avg_attempts = paid_invoices.groupby("invoice_id")["attempt_number"].max().mean()
                metrics["avg_attempts_to_payment"] = avg_attempts
        
        return metrics 