"""Transform UCI Online Retail dataset to CashFlowGuard format."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import typer

app = typer.Typer()


@app.command()
def transform(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to Online Retail.xlsx"),
    output_dir: Path = typer.Option(Path("data/uci"), "--output", "-o")
) -> None:
    """Transform UCI Online Retail data to CashFlowGuard format."""
    
    print(f"Loading UCI Online Retail dataset from {input_file}...")
    df = pd.read_excel(input_file)
    print(f"Loaded {len(df)} transactions")
    
    # Clean data
    print("\nCleaning data...")
    df = df[~df['InvoiceNo'].astype(str).str.startswith('C')]
    df = df[df['CustomerID'].notna()]
    df = df[(df['Quantity'] > 0) & (df['UnitPrice'] > 0)]
    df['InvoiceAmount'] = df['Quantity'] * df['UnitPrice']
    print(f"After cleaning: {len(df)} transactions")
    
    # Create Customers
    print("\nCreating customers.csv...")
    customers = df.groupby('CustomerID').agg({
        'Country': 'first',
        'InvoiceDate': 'min',
        'InvoiceAmount': 'sum'
    }).reset_index()
    
    customers['customer_id'] = 'CUST-' + customers['CustomerID'].astype(int).astype(str).str.zfill(5)
    customers['name'] = 'Customer ' + customers['CustomerID'].astype(int).astype(str)
    customers['email'] = customers['customer_id'].str.lower() + '@company.com'
    customers['phone'] = '+44-' + np.random.randint(100000000, 999999999, len(customers)).astype(str)    
    industry_map = {
        'United Kingdom': 'Retail', 'Germany': 'Manufacturing', 'France': 'Retail',
        'Netherlands': 'Professional Services', 'Switzerland': 'Finance', 'Australia': 'Technology'
    }
    customers['industry'] = customers['Country'].map(industry_map).fillna('Retail')
    
    country_code_map = {
        'United Kingdom': 'UK', 'Germany': 'DE', 'France': 'FR', 'Spain': 'ES',
        'Netherlands': 'NL', 'Belgium': 'BE', 'Switzerland': 'CH', 'Australia': 'AU'
    }
    customers['country'] = customers['Country'].map(country_code_map).fillna('UK')
    customers['state'] = None
    customers['payment_terms_days'] = customers['InvoiceAmount'].apply(
        lambda x: 60 if x > 50000 else (45 if x > 20000 else 30)
    )
    customers['credit_limit'] = (customers['InvoiceAmount'] * 2).round(2)
    customers['created_at'] = customers['InvoiceDate'].dt.strftime('%Y-%m-%d')
    
    customers_final = customers[[
        'customer_id', 'name', 'email', 'phone', 'industry',
        'country', 'state', 'payment_terms_days', 'credit_limit', 'created_at'
    ]]
    print(f"Created {len(customers_final)} customers")
    
    # Create Invoices
    print("\nCreating invoices.csv...")
    invoices = df.groupby('InvoiceNo').agg({
        'CustomerID': 'first', 'InvoiceDate': 'first', 'InvoiceAmount': 'sum'
    }).reset_index()
    
    customer_map = dict(zip(customers['CustomerID'], customers['customer_id']))
    invoices['customer_id'] = invoices['CustomerID'].map(customer_map)
    invoices = invoices[invoices['customer_id'].notna()]
    
    invoices['invoice_id'] = 'INV-' + (invoices.index + 1).astype(str).str.zfill(6)
    invoices['issue_date'] = invoices['InvoiceDate'].dt.strftime('%Y-%m-%d')
    
    terms_map = dict(zip(customers['customer_id'], customers['payment_terms_days']))
    invoices['payment_terms'] = invoices['customer_id'].map(terms_map)
    invoices['due_date'] = (
        pd.to_datetime(invoices['issue_date']) + 
        pd.to_timedelta(invoices['payment_terms'].fillna(30), unit='D')
    ).dt.strftime('%Y-%m-%d')
    
    invoices['invoice_amount'] = invoices['InvoiceAmount'].round(2)
    invoices['currency'] = 'GBP'
    invoices['days_since_issue'] = (datetime.now() - pd.to_datetime(invoices['issue_date'])).dt.days
    invoices['paid_probability'] = invoices['days_since_issue'].apply(
        lambda x: 0.95 if x > 1000 else (0.85 if x > 500 else 0.60)
    )
    invoices['status'] = invoices['paid_probability'].apply(
        lambda x: 'paid' if np.random.random() < x else 'open'
    )
    invoices['invoice_type'] = 'one_time'
    invoices['channel'] = 'online'
    invoices['created_at'] = invoices['issue_date']
    
    invoices_final = invoices[[
        'invoice_id', 'customer_id', 'issue_date', 'due_date',
        'invoice_amount', 'currency', 'status', 'invoice_type', 'channel', 'created_at'
    ]]
    print(f"Created {len(invoices_final)} invoices")
    
    # Create Payments
    print("\nCreating payments.csv...")
    paid_invoices = invoices_final[invoices_final['status'] == 'paid'].copy()
    
    payments = []
    for idx, inv in paid_invoices.iterrows():
        due_date = pd.to_datetime(inv['due_date'])
        days_offset = np.random.randint(-5, 1) if np.random.random() < 0.60 else np.random.randint(1, 46)
        payment_date = due_date + timedelta(days=days_offset)
        if payment_date > datetime.now():
            payment_date = datetime.now() - timedelta(days=np.random.randint(1, 30))
        
        payments.append({
            'payment_id': f'PAY-{len(payments)+1:06d}',
            'invoice_id': inv['invoice_id'],
            'payment_date': payment_date.strftime('%Y-%m-%d'),
            'amount': inv['invoice_amount'],
            'method': np.random.choice(['bank_transfer', 'credit_card', 'ach', 'check']),
            'status': 'completed'
        })
    
    payments_df = pd.DataFrame(payments)
    print(f"Created {len(payments_df)} payments")
    
    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    customers_final.to_csv(output_dir / 'customers.csv', index=False)
    invoices_final.to_csv(output_dir / 'invoices.csv', index=False)
    payments_df[['payment_id', 'invoice_id', 'payment_date', 'amount', 'method', 'status']].to_csv(
        output_dir / 'payments.csv', index=False
    )
    
    print(f"\n✅ Transformation complete! Files saved to {output_dir}/")


if __name__ == "__main__":
    app()
