"""
Generate realistic B2B invoice dataset based on real-world patterns.

Simulates a mid-sized B2B SaaS/Services company with:
- 100 enterprise customers
- Mix of payment terms (Net 15, 30, 45, 60)
- Seasonal patterns
- Customer payment behaviors (on-time, slow, problematic)
- Industry variations
- Geographic distribution
"""

import random
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
import typer

app = typer.Typer()


# Real company name patterns
COMPANY_PREFIXES = [
    "Global", "Tech", "Data", "Cloud", "Enterprise", "Digital", "Smart", "Quantum",
    "Apex", "Summit", "Vertex", "Pinnacle", "Prime", "Elite", "Alpha", "Beta"
]

COMPANY_SUFFIXES = [
    "Solutions", "Technologies", "Systems", "Enterprises", "Corporation", "Group",
    "Industries", "Services", "Partners", "Ventures", "Holdings", "Labs"
]

INDUSTRIES = {
    "Technology": {"avg_payment_days": 35, "late_rate": 0.25, "avg_invoice": 25000},
    "Healthcare": {"avg_payment_days": 45, "late_rate": 0.35, "avg_invoice": 40000},
    "Finance": {"avg_payment_days": 28, "late_rate": 0.15, "avg_invoice": 50000},
    "Manufacturing": {"avg_payment_days": 50, "late_rate": 0.40, "avg_invoice": 35000},
    "Retail": {"avg_payment_days": 42, "late_rate": 0.30, "avg_invoice": 20000},
    "Education": {"avg_payment_days": 60, "late_rate": 0.45, "avg_invoice": 15000},
    "Government": {"avg_payment_days": 70, "late_rate": 0.50, "avg_invoice": 60000},
    "Professional Services": {"avg_payment_days": 32, "late_rate": 0.20, "avg_invoice": 18000},
}

# Payment behavior tiers
PAYMENT_BEHAVIORS = {
    "excellent": {"on_time_rate": 0.90, "avg_delay_when_late": 5, "probability": 0.20},
    "good": {"on_time_rate": 0.75, "avg_delay_when_late": 10, "probability": 0.35},
    "average": {"on_time_rate": 0.60, "avg_delay_when_late": 18, "probability": 0.30},
    "poor": {"on_time_rate": 0.40, "avg_delay_when_late": 35, "probability": 0.10},
    "problematic": {"on_time_rate": 0.20, "avg_delay_when_late": 60, "probability": 0.05},
}

COUNTRIES = {
    "US": 0.60,
    "UK": 0.15,
    "CA": 0.10,
    "DE": 0.05,
    "AU": 0.05,
    "FR": 0.03,
    "NL": 0.02,
}

US_STATES = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI", "VA", "WA", "MA"]


def generate_customer_name():
    """Generate realistic company name."""
    return f"{random.choice(COMPANY_PREFIXES)} {random.choice(COMPANY_SUFFIXES)}"


def select_payment_behavior():
    """Select payment behavior tier based on probability distribution."""
    behaviors = list(PAYMENT_BEHAVIORS.keys())
    probs = [PAYMENT_BEHAVIORS[b]["probability"] for b in behaviors]
    return random.choices(behaviors, weights=probs)[0]


def generate_customers(n: int) -> pd.DataFrame:
    """Generate realistic customer data."""
    customers = []
    
    for i in range(n):
        industry = random.choice(list(INDUSTRIES.keys()))
        country = random.choices(list(COUNTRIES.keys()), weights=list(COUNTRIES.values()))[0]
        
        # Payment terms based on industry and size
        terms_options = [15, 30, 45, 60]
        if industry in ["Government", "Healthcare"]:
            terms = random.choice([45, 60])
        elif industry in ["Finance", "Professional Services"]:
            terms = random.choice([15, 30])
        else:
            terms = random.choice(terms_options)
        
        # Credit limit based on industry avg invoice
        industry_stats = INDUSTRIES[industry]
        base_limit = industry_stats["avg_invoice"] * random.uniform(3, 8)
        
        # Assign payment behavior
        payment_behavior = select_payment_behavior()
        
        customers.append({
            "customer_id": f"CUST-{i+1:04d}",
            "name": generate_customer_name(),
            "email": f"ap{i}@{generate_customer_name().lower().replace(' ', '')[:15]}.com",
            "phone": f"+1-{random.randint(200,999)}-{random.randint(100,999)}-{random.randint(1000,9999)}",
            "industry": industry,
            "country": country,
            "state": random.choice(US_STATES) if country == "US" else None,
            "payment_terms_days": terms,
            "credit_limit": round(base_limit, 2),
            "created_at": (datetime.now() - timedelta(days=random.randint(365, 1095))).strftime("%Y-%m-%d"),
            "payment_behavior_tier": payment_behavior  # Hidden field for simulation
        })
    
    return pd.DataFrame(customers)


def generate_invoices(customers_df: pd.DataFrame, n: int, months: int) -> pd.DataFrame:
    """Generate realistic invoice data with seasonal patterns."""
    invoices = []
    start_date = datetime.now() - timedelta(days=months * 30)
    
    # Create monthly invoice patterns per customer
    for i in range(n):
        customer = customers_df.sample(1).iloc[0]
        industry_stats = INDUSTRIES[customer["industry"]]
        
        # Randomize issue date with seasonal patterns
        day_offset = random.randint(0, months * 30)
        issue_date = start_date + timedelta(days=day_offset)
        
        # Higher invoice amounts in Q4 (Oct-Dec) for enterprise
        month = issue_date.month
        seasonal_multiplier = 1.2 if month in [10, 11, 12] else 1.0
        
        # Invoice amount based on industry average + variation
        base_amount = industry_stats["avg_invoice"]
        amount = base_amount * random.uniform(0.3, 2.0) * seasonal_multiplier
        
        # Due date
        due_date = issue_date + timedelta(days=int(customer["payment_terms_days"]))
        
        # Status - 40% paid, 60% open (more realistic for AR)
        status = random.choices(["open", "paid"], weights=[0.60, 0.40])[0]
        
        # Invoice type
        if customer["industry"] in ["Technology", "Professional Services"]:
            invoice_type = random.choice(["recurring", "milestone", "one_time"])
        else:
            invoice_type = random.choice(["one_time", "recurring"])
        
        invoices.append({
            "invoice_id": f"INV-{i+1:05d}",
            "customer_id": customer["customer_id"],
            "issue_date": issue_date.strftime("%Y-%m-%d"),
            "due_date": due_date.strftime("%Y-%m-%d"),
            "invoice_amount": round(amount, 2),
            "currency": "USD",
            "status": status,
            "invoice_type": invoice_type,
            "channel": random.choice(["online", "offline"]),
            "created_at": issue_date.strftime("%Y-%m-%d"),
            "customer_behavior": customer["payment_behavior_tier"]  # For simulation
        })
    
    return pd.DataFrame(invoices)


def generate_payments(invoices_df: pd.DataFrame, customers_df: pd.DataFrame) -> pd.DataFrame:
    """Generate realistic payment data based on customer behavior."""
    payments = []
    payment_id = 1
    
    # Only paid invoices
    paid_invoices = invoices_df[invoices_df["status"] == "paid"].copy()
    
    for _, invoice in paid_invoices.iterrows():
        due_date = datetime.strptime(invoice["due_date"], "%Y-%m-%d")
        behavior_tier = invoice["customer_behavior"]
        behavior = PAYMENT_BEHAVIORS[behavior_tier]
        
        # Determine if paid on time or late
        if random.random() < behavior["on_time_rate"]:
            # On time (0-3 days before due date)
            days_offset = random.randint(-3, 0)
        else:
            # Late - use behavior-specific delay
            avg_delay = behavior["avg_delay_when_late"]
            # Add some randomness
            days_offset = int(np.random.gamma(2, avg_delay / 2))
        
        payment_date = due_date + timedelta(days=days_offset)
        
        # Don't pay in the future
        if payment_date > datetime.now():
            payment_date = datetime.now() - timedelta(days=random.randint(1, 10))
        
        # Payment method distribution
        method_weights = {
            "bank_transfer": 0.45,
            "ach": 0.30,
            "credit_card": 0.15,
            "check": 0.07,
            "wire": 0.03,
        }
        method = random.choices(list(method_weights.keys()), weights=list(method_weights.values()))[0]
        
        payments.append({
            "payment_id": f"PAY-{payment_id:05d}",
            "invoice_id": invoice["invoice_id"],
            "payment_date": payment_date.strftime("%Y-%m-%d"),
            "amount": invoice["invoice_amount"],
            "method": method,
            "status": "completed"
        })
        payment_id += 1
    
    return pd.DataFrame(payments)


@app.command()
def generate(
    customers: int = typer.Option(100, "--customers", "-c"),
    invoices: int = typer.Option(800, "--invoices", "-i"),
    months: int = typer.Option(12, "--months", "-m"),
    output_dir: Path = typer.Option(Path("data/real"), "--output", "-o")
) -> None:
    """Generate realistic B2B dataset."""
    print(f"Generating realistic B2B dataset...")
    print(f"  Customers: {customers}")
    print(f"  Invoices: {invoices}")
    print(f"  Period: {months} months")
    print(f"  Industries: {len(INDUSTRIES)}")
    
    # Generate data
    print("\n1. Generating customers...")
    customers_df = generate_customers(customers)
    
    # Remove hidden field before saving
    customers_save = customers_df.drop("payment_behavior_tier", axis=1)
    
    print("2. Generating invoices...")
    invoices_df = generate_invoices(customers_df, invoices, months)
    
    print("3. Generating payments...")
    payments_df = generate_payments(invoices_df, customers_df)
    
    # Remove hidden fields
    invoices_save = invoices_df.drop("customer_behavior", axis=1)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    customers_save.to_csv(output_dir / "customers.csv", index=False)
    invoices_save.to_csv(output_dir / "invoices.csv", index=False)
    payments_df.to_csv(output_dir / "payments.csv", index=False)
    
    # Statistics
    open_invoices = invoices_df[invoices_df["status"] == "open"]
    late_payments = payments_df.merge(invoices_df[["invoice_id", "due_date"]], on="invoice_id")
    late_payments["days_diff"] = (
        pd.to_datetime(late_payments["payment_date"]) - 
        pd.to_datetime(late_payments["due_date"])
    ).dt.days
    late_rate = (late_payments["days_diff"] > 0).mean() * 100
    
    print(f"\n✓ Data generated successfully!")
    print(f"\n📊 Statistics:")
    print(f"  Total Customers: {len(customers_df)}")
    print(f"  Total Invoices: {len(invoices_df)}")
    print(f"    Open: {len(open_invoices)} ({len(open_invoices)/len(invoices_df)*100:.1f}%)")
    print(f"    Paid: {len(invoices_df[invoices_df['status'] == 'paid'])} ({len(invoices_df[invoices_df['status'] == 'paid'])/len(invoices_df)*100:.1f}%)")
    print(f"  Total Payments: {len(payments_df)}")
    print(f"  Late Payment Rate: {late_rate:.1f}%")
    print(f"  Total AR: ${open_invoices['invoice_amount'].sum():,.2f}")
    print(f"  Avg Invoice: ${invoices_df['invoice_amount'].mean():,.2f}")
    
    # Industry breakdown
    print(f"\n📈 By Industry:")
    for industry in customers_df["industry"].value_counts().head(5).items():
        print(f"  {industry[0]}: {industry[1]} customers")
    
    print(f"\n💾 Files saved to {output_dir}/")


if __name__ == "__main__":
    app()
