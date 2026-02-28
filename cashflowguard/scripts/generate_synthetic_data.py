"""Generate synthetic data for testing CashFlowGuard."""

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import typer

app = typer.Typer()


def generate_customers(n: int) -> pd.DataFrame:
    """Generate synthetic customers."""
    industries = ["Technology", "Healthcare", "Retail", "Manufacturing", "Finance", "Services"]
    countries = ["US"] * 80 + ["CA"] * 10 + ["UK"] * 10
    states = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
    
    customers = []
    for i in range(n):
        customer_id = f"CUST-{i+1:04d}"
        customers.append({
            "customer_id": customer_id,
            "name": f"Company {chr(65 + i % 26)}{i // 26}",
            "email": f"billing{i}@company{i}.com",
            "phone": f"555-{random.randint(1000, 9999)}",
            "industry": random.choice(industries),
            "country": random.choice(countries),
            "state": random.choice(states) if random.choice(countries) == "US" else None,
            "payment_terms_days": random.choice([15, 30, 45, 60]),
            "credit_limit": random.choice([10000, 25000, 50000, 100000, 250000]),
            "created_at": (datetime.now() - timedelta(days=random.randint(180, 1095))).strftime("%Y-%m-%d")
        })
    
    return pd.DataFrame(customers)


def generate_invoices(customers_df: pd.DataFrame, n: int, months: int) -> pd.DataFrame:
    """Generate synthetic invoices."""
    invoice_types = ["one_time", "recurring", "milestone"]
    channels = ["online", "offline"]
    
    invoices = []
    start_date = datetime.now() - timedelta(days=months * 30)
    
    for i in range(n):
        customer = customers_df.sample(1).iloc[0]
        
        issue_date = start_date + timedelta(days=random.randint(0, months * 30))
        payment_terms = int(customer["payment_terms_days"])
        due_date = issue_date + timedelta(days=payment_terms)
        
        # 70% open, 30% paid
        status = random.choices(["open", "paid"], weights=[0.7, 0.3])[0]
        
        # Amount based on customer credit limit
        max_amount = customer["credit_limit"] * 0.3
        amount = random.uniform(500, max_amount)
        
        invoices.append({
            "invoice_id": f"INV-{i+1:05d}",
            "customer_id": customer["customer_id"],
            "issue_date": issue_date.strftime("%Y-%m-%d"),
            "due_date": due_date.strftime("%Y-%m-%d"),
            "invoice_amount": round(amount, 2),
            "currency": "USD",
            "status": status,
            "invoice_type": random.choice(invoice_types),
            "channel": random.choice(channels),
            "created_at": issue_date.strftime("%Y-%m-%d")
        })
    
    return pd.DataFrame(invoices)


def generate_payments(invoices_df: pd.DataFrame) -> pd.DataFrame:
    """Generate synthetic payments."""
    methods = ["bank_transfer", "credit_card", "check", "ach"]
    
    payments = []
    payment_id = 1
    
    # Generate payments for paid invoices
    paid_invoices = invoices_df[invoices_df["status"] == "paid"]
    
    for _, invoice in paid_invoices.iterrows():
        due_date = datetime.strptime(invoice["due_date"], "%Y-%m-%d")
        
        # 60% pay on time, 40% pay late
        if random.random() < 0.6:
            # On time (before or on due date)
            days_offset = random.randint(-5, 0)
        else:
            # Late (after due date)
            days_offset = random.randint(1, 60)
        
        payment_date = due_date + timedelta(days=days_offset)
        
        # Ensure payment date is not in future
        if payment_date > datetime.now():
            payment_date = datetime.now() - timedelta(days=random.randint(1, 30))
        
        payments.append({
            "payment_id": f"PAY-{payment_id:05d}",
            "invoice_id": invoice["invoice_id"],
            "payment_date": payment_date.strftime("%Y-%m-%d"),
            "amount": invoice["invoice_amount"],
            "method": random.choice(methods),
            "status": "completed"
        })
        payment_id += 1
    
    return pd.DataFrame(payments)


@app.command()
def generate(
    customers: int = typer.Option(100, "--customers", "-c"),
    invoices: int = typer.Option(500, "--invoices", "-i"),
    months: int = typer.Option(12, "--months", "-m"),
    output_dir: Path = typer.Option(Path("data/sample"), "--output", "-o")
) -> None:
    """Generate synthetic data."""
    print(f"Generating synthetic data...")
    print(f"  Customers: {customers}")
    print(f"  Invoices: {invoices}")
    print(f"  Period: {months} months")
    
    # Generate data
    customers_df = generate_customers(customers)
    invoices_df = generate_invoices(customers_df, invoices, months)
    payments_df = generate_payments(invoices_df)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save to CSV
    customers_df.to_csv(output_dir / "customers.csv", index=False)
    invoices_df.to_csv(output_dir / "invoices.csv", index=False)
    payments_df.to_csv(output_dir / "payments.csv", index=False)
    
    print(f"\n✓ Data generated successfully!")
    print(f"  Customers: {len(customers_df)}")
    print(f"  Invoices: {len(invoices_df)}")
    print(f"    Open: {len(invoices_df[invoices_df['status'] == 'open'])}")
    print(f"    Paid: {len(invoices_df[invoices_df['status'] == 'paid'])}")
    print(f"  Payments: {len(payments_df)}")
    print(f"\nFiles saved to {output_dir}/")


if __name__ == "__main__":
    app()
