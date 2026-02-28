"""
Action logger for tracking all collections activities.

Maintains an audit trail of:
- Every action taken (email sent, call made, etc.)
- Outcomes and responses
- Payment results
- Success metrics

Uses SQLite for persistence.
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd
import json


class ActionLogger:
    """Log and track all collections actions with SQLite backend."""
    
    def __init__(self, db_path: str = "collections_audit.db"):
        """
        Initialize action logger.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Actions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_date TIMESTAMP NOT NULL,
                scheduled_date TIMESTAMP,
                channel TEXT,
                message_sent TEXT,
                sent_by TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Responses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                response_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                response_date TIMESTAMP NOT NULL,
                response_type TEXT,
                response_text TEXT,
                payment_promised BOOLEAN,
                payment_plan_accepted BOOLEAN,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (action_id) REFERENCES actions (action_id)
            )
        """)
        
        # Outcomes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT NOT NULL,
                action_id INTEGER,
                outcome_type TEXT NOT NULL,
                outcome_date TIMESTAMP NOT NULL,
                amount_collected REAL,
                days_to_payment INTEGER,
                payment_method TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (action_id) REFERENCES actions (action_id)
            )
        """)
        
        # Success metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS success_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_date DATE NOT NULL,
                action_type TEXT,
                total_actions INTEGER,
                successful_actions INTEGER,
                total_amount_targeted REAL,
                total_amount_collected REAL,
                avg_days_to_payment REAL,
                success_rate REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_invoice ON actions(invoice_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_date ON actions(action_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_invoice ON outcomes(invoice_id)")
        
        conn.commit()
        conn.close()
    
    def log_action(
        self,
        invoice_id: str,
        customer_id: str,
        action_type: str,
        channel: str = "email",
        message_sent: str = None,
        scheduled_date: datetime = None,
        sent_by: str = "system",
        notes: str = None
    ) -> int:
        """
        Log a collections action.
        
        Args:
            invoice_id: Invoice identifier
            customer_id: Customer identifier
            action_type: Type of action (reminder, notice, call, etc.)
            channel: Communication channel (email, sms, phone, letter)
            message_sent: Content of message sent
            scheduled_date: Originally scheduled date
            sent_by: Who sent it (person name or 'system')
            notes: Additional notes
            
        Returns:
            action_id of logged action
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO actions (
                invoice_id, customer_id, action_type, action_date,
                scheduled_date, channel, message_sent, sent_by, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_id,
            customer_id,
            action_type,
            datetime.now(),
            scheduled_date,
            channel,
            message_sent,
            sent_by,
            notes
        ))
        
        action_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return action_id
    
    def log_response(
        self,
        action_id: int,
        response_type: str,
        response_text: str = None,
        payment_promised: bool = False,
        payment_plan_accepted: bool = False,
        notes: str = None
    ) -> int:
        """
        Log customer response to an action.
        
        Args:
            action_id: ID of action being responded to
            response_type: Type of response (email, call, no_response)
            response_text: Content of response
            payment_promised: Customer promised payment
            payment_plan_accepted: Customer accepted payment plan
            notes: Additional notes
            
        Returns:
            response_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO responses (
                action_id, response_date, response_type, response_text,
                payment_promised, payment_plan_accepted, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            action_id,
            datetime.now(),
            response_type,
            response_text,
            payment_promised,
            payment_plan_accepted,
            notes
        ))
        
        response_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return response_id
    
    def log_outcome(
        self,
        invoice_id: str,
        outcome_type: str,
        action_id: int = None,
        amount_collected: float = None,
        days_to_payment: int = None,
        payment_method: str = None,
        notes: str = None
    ) -> int:
        """
        Log final outcome for an invoice.
        
        Args:
            invoice_id: Invoice identifier
            outcome_type: Type of outcome (paid, partial, plan, escalated, written_off)
            action_id: Last action ID that led to this outcome
            amount_collected: Amount actually collected
            days_to_payment: Days from first action to payment
            payment_method: How payment was made
            notes: Additional notes
            
        Returns:
            outcome_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO outcomes (
                invoice_id, action_id, outcome_type, outcome_date,
                amount_collected, days_to_payment, payment_method, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_id,
            action_id,
            outcome_type,
            datetime.now(),
            amount_collected,
            days_to_payment,
            payment_method,
            notes
        ))
        
        outcome_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return outcome_id
    
    def get_invoice_history(self, invoice_id: str) -> pd.DataFrame:
        """
        Get complete action history for an invoice.
        
        Args:
            invoice_id: Invoice to query
            
        Returns:
            DataFrame with all actions, responses, and outcomes
        """
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT 
                a.action_id,
                a.action_date,
                a.action_type,
                a.channel,
                a.sent_by,
                r.response_type,
                r.response_date,
                r.payment_promised,
                o.outcome_type,
                o.amount_collected
            FROM actions a
            LEFT JOIN responses r ON a.action_id = r.action_id
            LEFT JOIN outcomes o ON a.invoice_id = o.invoice_id
            WHERE a.invoice_id = ?
            ORDER BY a.action_date DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(invoice_id,))
        conn.close()
        
        return df
    
    def get_customer_history(self, customer_id: str) -> pd.DataFrame:
        """
        Get all actions for a customer across all invoices.
        
        Args:
            customer_id: Customer to query
            
        Returns:
            DataFrame with customer action history
        """
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT 
                a.invoice_id,
                a.action_date,
                a.action_type,
                a.channel,
                r.response_type,
                o.outcome_type
            FROM actions a
            LEFT JOIN responses r ON a.action_id = r.action_id
            LEFT JOIN outcomes o ON a.invoice_id = o.invoice_id
            WHERE a.customer_id = ?
            ORDER BY a.action_date DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(customer_id,))
        conn.close()
        
        return df
    
    def calculate_success_metrics(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        action_type: str = None
    ) -> Dict:
        """
        Calculate success metrics for actions.
        
        Args:
            start_date: Start of period
            end_date: End of period  
            action_type: Filter by action type
            
        Returns:
            Dictionary with success metrics
        """
        conn = sqlite3.connect(self.db_path)
        
        # Build query based on filters
        where_clauses = []
        params = []
        
        if start_date:
            where_clauses.append("a.action_date >= ?")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("a.action_date <= ?")
            params.append(end_date)
        
        if action_type:
            where_clauses.append("a.action_type = ?")
            params.append(action_type)
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
            SELECT 
                COUNT(DISTINCT a.action_id) as total_actions,
                COUNT(DISTINCT CASE WHEN o.outcome_type = 'paid' THEN a.action_id END) as successful_actions,
                COUNT(DISTINCT CASE WHEN r.response_id IS NOT NULL THEN a.action_id END) as got_response,
                AVG(CASE WHEN o.days_to_payment IS NOT NULL THEN o.days_to_payment END) as avg_days_to_payment,
                SUM(CASE WHEN o.amount_collected IS NOT NULL THEN o.amount_collected ELSE 0 END) as total_collected
            FROM actions a
            LEFT JOIN responses r ON a.action_id = r.action_id
            LEFT JOIN outcomes o ON a.action_id = o.action_id
            WHERE {where_clause}
        """
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        conn.close()
        
        total_actions = result[0] or 0
        successful_actions = result[1] or 0
        got_response = result[2] or 0
        
        return {
            "total_actions": total_actions,
            "successful_actions": successful_actions,
            "success_rate": successful_actions / total_actions if total_actions > 0 else 0,
            "response_rate": got_response / total_actions if total_actions > 0 else 0,
            "avg_days_to_payment": result[3] or 0,
            "total_amount_collected": result[4] or 0
        }
    
    def get_action_effectiveness_report(self) -> pd.DataFrame:
        """
        Generate report on effectiveness by action type.
        
        Returns:
            DataFrame with metrics per action type
        """
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT 
                a.action_type,
                COUNT(DISTINCT a.action_id) as total_sent,
                COUNT(DISTINCT r.response_id) as responses_received,
                COUNT(DISTINCT CASE WHEN o.outcome_type = 'paid' THEN o.outcome_id END) as payments_received,
                AVG(o.days_to_payment) as avg_days_to_payment,
                SUM(o.amount_collected) as total_collected
            FROM actions a
            LEFT JOIN responses r ON a.action_id = r.action_id
            LEFT JOIN outcomes o ON a.action_id = o.action_id
            GROUP BY a.action_type
            ORDER BY payments_received DESC
        """
        
        df = pd.read_sql_query(query, conn)
        
        # Calculate rates
        df["response_rate"] = (df["responses_received"] / df["total_sent"] * 100).round(2)
        df["payment_rate"] = (df["payments_received"] / df["total_sent"] * 100).round(2)
        
        conn.close()
        
        return df
    
    def export_audit_log(
        self,
        output_path: str,
        start_date: datetime = None,
        end_date: datetime = None
    ):
        """
        Export complete audit log to CSV.
        
        Args:
            output_path: Where to save CSV
            start_date: Optional start date filter
            end_date: Optional end date filter
        """
        conn = sqlite3.connect(self.db_path)
        
        where_clauses = []
        params = []
        
        if start_date:
            where_clauses.append("a.action_date >= ?")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("a.action_date <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
            SELECT 
                a.action_id,
                a.invoice_id,
                a.customer_id,
                a.action_type,
                a.action_date,
                a.channel,
                a.sent_by,
                r.response_type,
                r.response_date,
                r.payment_promised,
                o.outcome_type,
                o.amount_collected,
                o.days_to_payment,
                a.notes
            FROM actions a
            LEFT JOIN responses r ON a.action_id = r.action_id
            LEFT JOIN outcomes o ON a.invoice_id = o.invoice_id
            WHERE {where_clause}
            ORDER BY a.action_date DESC
        """
        
        df = pd.read_sql_query(query, conn, params=params)
        df.to_csv(output_path, index=False)
        
        conn.close()
        
        return output_path