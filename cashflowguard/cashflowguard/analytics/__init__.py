"""Analytics modules for CashFlowGuard."""

from cashflowguard.analytics.aging import (
    calculate_aging,
    get_aging_summary,
    get_aging_trend,
    get_customer_aging,
)
from cashflowguard.analytics.ar_metrics import (
    calculate_ar_summary,
    calculate_collection_effectiveness_index,
    calculate_customer_risk_scores,
    calculate_dso,
    calculate_payment_behavior,
)
from cashflowguard.analytics.forecasting import (
    analyze_collection_impact,
    calculate_cash_gap,
    forecast_cash_inflows,
    simulate_cash_scenarios,
)

__all__ = [
    "calculate_aging",
    "get_aging_summary",
    "get_customer_aging",
    "get_aging_trend",
    "calculate_dso",
    "calculate_collection_effectiveness_index",
    "calculate_payment_behavior",
    "calculate_customer_risk_scores",
    "calculate_ar_summary",
    "forecast_cash_inflows",
    "simulate_cash_scenarios",
    "analyze_collection_impact",
    "calculate_cash_gap",
]
