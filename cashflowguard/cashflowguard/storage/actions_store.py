"""Actions storage and management."""

from datetime import datetime
from typing import Optional
import uuid


def generate_action_id() -> str:
    """Generate unique action ID."""
    return f"ACT-{str(uuid.uuid4())[:8].upper()}"


def record_action(
    invoice_id: str,
    action_type: str,
    notes: Optional[str] = None,
    outcome: str = "pending"
) -> dict:
    """
    Record a collection action.
    
    Args:
        invoice_id: Invoice ID
        action_type: Type of action
        notes: Optional notes
        outcome: Action outcome
        
    Returns:
        Dictionary with action details
    """
    return {
        "action_id": generate_action_id(),
        "invoice_id": invoice_id,
        "action_type": action_type,
        "action_date": datetime.now().isoformat(),
        "notes": notes or "",
        "outcome": outcome
    }
