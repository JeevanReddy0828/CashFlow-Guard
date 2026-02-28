"""
Standalone Outreach Tool - Generate Personalized Collection Messages
Run: python outreach_standalone.py
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def load_data(data_dir):
    """Load data files"""
    data_path = Path(data_dir)
    customers = pd.read_csv(data_path / "customers.csv")
    invoices = pd.read_csv(data_path / "invoices.csv")
    payments = pd.read_csv(data_path / "payments.csv")
    
    # Parse dates
    invoices["due_date"] = pd.to_datetime(invoices["due_date"], errors='coerce')
    invoices["issue_date"] = pd.to_datetime(invoices["issue_date"], errors='coerce')
    
    return customers, invoices, payments

def generate_email(customer_name, invoice_id, invoice_amount, due_date, days_overdue, action_type):
    """Generate email template"""
    
    templates = {
        "friendly_reminder": {
            "subject": f"Friendly Reminder: Invoice #{invoice_id} - ${invoice_amount:,.2f}",
            "body": f"""Dear {customer_name},

I hope this message finds you well!

This is a friendly reminder that Invoice #{invoice_id} for ${invoice_amount:,.2f} was due on {due_date.strftime('%B %d, %Y')} ({days_overdue} days ago).

We understand that oversights happen, and we wanted to reach out to see if there's anything we can help with regarding this payment.

Invoice Details:
• Invoice Number: {invoice_id}
• Amount Due: ${invoice_amount:,.2f}
• Original Due Date: {due_date.strftime('%B %d, %Y')}
• Days Overdue: {days_overdue}

If you've already sent payment, please disregard this message. If you have any questions, please contact us.

Thank you for your business!

Best regards,
Accounts Receivable Team
"""
        },
        "second_notice": {
            "subject": f"SECOND NOTICE: Invoice #{invoice_id} - Payment Required",
            "body": f"""Dear {customer_name},

This is our second notice regarding Invoice #{invoice_id} for ${invoice_amount:,.2f}, which is now {days_overdue} days overdue.

Outstanding Invoice:
• Invoice Number: {invoice_id}
• Amount Due: ${invoice_amount:,.2f}
• Due Date: {due_date.strftime('%B %d, %Y')}
• Days Overdue: {days_overdue}

IMPORTANT: To avoid any interruption in service, please remit payment within the next 5 business days.

If you are experiencing difficulty making this payment, please contact us to discuss options.

Sincerely,
Accounts Receivable Department
"""
        }
    }
    
    return templates.get(action_type, templates["friendly_reminder"])

def main():
    print("\n" + "="*60)
    print("📧 CashFlowGuard Outreach - Message Generator")
    print("="*60 + "\n")
    
    # Configuration
    DATA_DIR = "E:/CashFlowGuard/data/uci"
    TOP_N = 20
    ACTION_TYPE = "friendly_reminder"  # or "second_notice"
    COMPANY_NAME = "Your Company"
    
    print(f"Loading data from: {DATA_DIR}")
    customers, invoices, payments = load_data(DATA_DIR)
    print(f"✓ Loaded {len(invoices):,} invoices, {len(customers):,} customers\n")
    
    # Get open overdue invoices
    open_invoices = invoices[invoices["status"] == "open"].copy()
    now = pd.Timestamp.now()
    open_invoices["days_overdue"] = (now - open_invoices["due_date"]).dt.days.clip(lower=0)
    
    # Get top overdue
    target = open_invoices.nlargest(TOP_N, "days_overdue")
    
    print(f"Generating {ACTION_TYPE} messages for top {len(target)} overdue invoices...\n")
    
    messages = []
    
    for _, invoice in target.iterrows():
        # Get customer
        customer = customers[customers["customer_id"] == invoice["customer_id"]]
        if len(customer) == 0:
            continue
        customer = customer.iloc[0]
        
        # Generate email
        email = generate_email(
            customer_name=customer.get("name", invoice["customer_id"]),
            invoice_id=invoice["invoice_id"],
            invoice_amount=invoice["invoice_amount"],
            due_date=invoice["due_date"],
            days_overdue=int(invoice["days_overdue"]),
            action_type=ACTION_TYPE
        )
        
        messages.append({
            "invoice_id": invoice["invoice_id"],
            "customer_id": invoice["customer_id"],
            "customer_name": customer.get("name", ""),
            "customer_email": customer.get("email", ""),
            "invoice_amount": invoice["invoice_amount"],
            "days_overdue": int(invoice["days_overdue"]),
            "action_type": ACTION_TYPE,
            "email_subject": email["subject"],
            "email_body": email["body"]
        })
    
    # Save to CSV
    messages_df = pd.DataFrame(messages)
    output_file = "collection_messages.csv"
    messages_df.to_csv(output_file, index=False)
    
    # Display summary
    print("="*60)
    print(f"✓ Generated {len(messages)} messages")
    print(f"✓ Saved to: {output_file}")
    print("="*60 + "\n")
    
    # Show first 3
    print("Preview (First 3 Messages):\n")
    for i, msg in enumerate(messages[:3], 1):
        print(f"\n{'─'*60}")
        print(f"Message {i}: {msg['invoice_id']} - {msg['customer_name']}")
        print(f"{'─'*60}")
        print(f"To: {msg['customer_email']}")
        print(f"Amount: ${msg['invoice_amount']:,.2f} | Days Overdue: {msg['days_overdue']}")
        print(f"\nSubject: {msg['email_subject']}")
        print(f"\n{msg['email_body'][:300]}...")
    
    print(f"\n\n📥 Full messages saved to: {output_file}")
    print(f"   Open in Excel or any CSV viewer\n")

if __name__ == "__main__":
    main()
