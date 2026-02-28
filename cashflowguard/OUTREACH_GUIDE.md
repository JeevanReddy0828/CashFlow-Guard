# 📧 CashFlowGuard - Complete Collections Automation

## 🎯 **NEW FEATURES - Complete Integration Guide**

CashFlowGuard now includes **complete collections automation** with:
- ✅ Personalized email/SMS template generation
- ✅ Automated follow-up scheduling
- ✅ Action logging and audit trails
- ✅ Success metrics tracking

---

## 🚀 **Quick Start - Full Workflow**

### **1. Generate Risk-Prioritized Collections Plan**

```bash
# Generate plan for top 50 invoices
cashflowguard plan --data-dir data/uci --top 50
```

### **2. Generate Personalized Messages**

```bash
# Create personalized emails for top 20 risky invoices
cashflowguard outreach \
    --data-dir data/uci \
    --top 20 \
    --action-type friendly_reminder \
    --company-name "Your Business Name" \
    --output messages_to_send.csv
```

**Output**: `messages_to_send.csv` with personalized email subject/body and SMS text

### **3. Create Follow-Up Schedule**

```bash
# Generate automated follow-up schedule
cashflowguard schedule \
    --data-dir data/uci \
    --max-attempts 6 \
    --output followup_schedule.csv
```

### **4. Log Actions Taken**

```python
from action_logger import ActionLogger

logger = ActionLogger()

# Log that you sent an email
action_id = logger.log_action(
    invoice_id="INV001",
    customer_id="CUST123",
    action_type="friendly_reminder",
    channel="email",
    message_sent="[Full email text]",
    sent_by="John Doe"
)

# Log customer response
logger.log_response(
    action_id=action_id,
    response_type="email",
    payment_promised=True,
    notes="Customer will pay by Friday"
)

# Log final outcome
logger.log_outcome(
    invoice_id="INV001",
    outcome_type="paid",
    amount_collected=5000.00,
    days_to_payment=3
)
```

### **5. Track Success Metrics**

```bash
# View last 30 days metrics
cashflowguard metrics --days 30

# Export detailed metrics
cashflowguard metrics --days 90 --export metrics_report.csv
```

---

## 📧 **Email Template Examples**

### **Friendly Reminder**
```python
from message_generator import MessageGenerator

msg_gen = MessageGenerator(
    company_name="Acme Corp",
    company_phone="(555) 123-4567",
    company_email="ar@acme.com"
)

email = msg_gen.generate_email(
    customer_name="John Smith",
    invoice_id="INV-2024-001",
    invoice_amount=5000.00,
    due_date=datetime(2024, 1, 15),
    days_overdue=7,
    action_type="friendly_reminder",
    risk_level="medium"
)

print(email["subject"])
# Output: "Friendly Reminder: Invoice #INV-2024-001 - $5,000.00"

print(email["body"])
# Output: Full personalized email text
```

### **Available Action Types**
1. `friendly_reminder` - Gentle first contact
2. `second_notice` - More urgent follow-up
3. `call_request` - Request phone discussion
4. `escalate` - Final notice before collections
5. `payment_plan` - Offer installment options
6. `thank_you` - Confirmation of payment

---

## 📅 **Scheduling System**

### **Automatic Cadence by Risk Level**

```python
from collections_scheduler import CollectionsScheduler

scheduler = CollectionsScheduler()

# Get cadence rules
print(scheduler.get_cadence_summary())
```

**Output:**
```
risk_level       total_attempts  cadence_days           total_duration_days
low_risk         4               7, 14, 21, 30         30
medium_risk      5               5, 10, 15, 22, 30     30
high_risk        6               3, 7, 10, 14, 17, 21  21
very_high_risk   7               1, 3, 5, 7, 9, 12, 15 15
```

### **Generate Weekly Collections Plan**

```python
# Get this week's actions
weekly_plan = scheduler.generate_weekly_plan(invoices_df)

print(f"Actions due this week: {len(weekly_plan)}")
print(weekly_plan[["invoice_id", "scheduled_date", "action_type", "priority_score"]])
```

### **Reschedule or Cancel Actions**

```python
# Reschedule an action
scheduler.reschedule_action(
    schedule_df=schedule,
    invoice_id="INV001",
    attempt_number=2,
    new_date=datetime(2024, 2, 20),
    reason="Customer requested delay"
)

# Cancel all future actions (payment received)
scheduler.cancel_future_actions(
    schedule_df=schedule,
    invoice_id="INV001",
    reason="Payment received"
)
```

---

## 📊 **Action Logger - Audit Trail**

### **Complete Action History**

```python
from action_logger import ActionLogger

logger = ActionLogger("collections_audit.db")

# View invoice history
history = logger.get_invoice_history("INV001")
print(history)
```

**Output:**
```
action_id  action_date  action_type        channel  response_type  outcome_type  amount_collected
1          2024-02-01   friendly_reminder  email    email          paid          5000.00
2          2024-01-25   friendly_reminder  email    None           None          None
```

### **Success Metrics**

```python
# Calculate success rate
metrics = logger.calculate_success_metrics(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 2, 1),
    action_type="friendly_reminder"
)

print(f"Success Rate: {metrics['success_rate']:.1%}")
print(f"Response Rate: {metrics['response_rate']:.1%}")
print(f"Avg Days to Payment: {metrics['avg_days_to_payment']:.1f}")
print(f"Total Collected: ${metrics['total_amount_collected']:,.2f}")
```

### **Export Audit Log**

```python
# Export complete audit trail
logger.export_audit_log(
    output_path="audit_2024_Q1.csv",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 3, 31)
)
```

---

## 🔄 **Complete Workflow Example**

### **Scenario: Weekly Collections Routine**

```python
from cashflowguard.core.loader import DataLoader
from cashflowguard.ml.predict import score_invoices
from message_generator import MessageGenerator
from collections_scheduler import CollectionsScheduler
from action_logger import ActionLogger

# 1. Load and score invoices
loader = DataLoader("data/uci")
customers_df, invoices_df, payments_df, _ = loader.load_all()
scored_df = score_invoices(invoices_df, customers_df, payments_df, "models/model.pkl")

# 2. Get this week's scheduled actions
scheduler = CollectionsScheduler()
schedule_df = pd.read_csv("followup_schedule.csv")
weekly_actions = scheduler.get_this_weeks_actions(schedule_df)

# 3. Generate messages for each action
msg_gen = MessageGenerator(company_name="Your Company")
logger = ActionLogger()

for _, action in weekly_actions.iterrows():
    invoice = scored_df[scored_df["invoice_id"] == action["invoice_id"]].iloc[0]
    customer = customers_df[customers_df["customer_id"] == action["customer_id"]].iloc[0]
    
    # Generate email
    email = msg_gen.generate_email(
        customer_name=customer["name"],
        invoice_id=invoice["invoice_id"],
        invoice_amount=invoice["invoice_amount"],
        due_date=invoice["due_date"],
        days_overdue=action["estimated_days_overdue"],
        action_type=action["action_type"],
        risk_level=invoice["risk_category"]
    )
    
    # Send email (integrate with your email service)
    # send_email(to=customer["email"], subject=email["subject"], body=email["body"])
    
    # Log action
    logger.log_action(
        invoice_id=invoice["invoice_id"],
        customer_id=customer["customer_id"],
        action_type=action["action_type"],
        channel="email",
        message_sent=email["body"],
        scheduled_date=action["scheduled_date"],
        sent_by="AutoSystem"
    )
    
    # Mark as completed
    scheduler.mark_completed(
        schedule_df=schedule_df,
        invoice_id=invoice["invoice_id"],
        attempt_number=action["attempt_number"],
        notes="Sent successfully"
    )

# 4. Save updated schedule
schedule_df.to_csv("followup_schedule.csv", index=False)

# 5. View weekly summary
metrics = logger.calculate_success_metrics(
    start_date=datetime.now() - timedelta(days=7)
)
print(f"This Week: {metrics['total_actions']} actions, {metrics['success_rate']:.1%} success")
```

---

## 📈 **Success Tracking Dashboard**

### **View Effectiveness Report**

```python
effectiveness = logger.get_action_effectiveness_report()
print(effectiveness)
```

**Output:**
```
action_type         total_sent  responses_received  payments_received  response_rate  payment_rate
friendly_reminder   145         87                  52                60.0%          35.9%
second_notice       78          45                  31                57.7%          39.7%
call_request        34          28                  24                82.4%          70.6%
payment_plan        12          11                  9                 91.7%          75.0%
escalate            8           6                   3                 75.0%          37.5%
```

---

## 🎯 **Best Practices**

### **1. Start Gentle, Escalate Gradually**
```python
# Let the system recommend next action
recommended = msg_gen.recommend_action(
    days_overdue=15,
    risk_score=75,
    previous_actions=["friendly_reminder", "second_notice"]
)
# Returns: "call_request"
```

### **2. Track Everything**
- Log every email sent
- Record every customer response
- Document final outcomes
- Analyze what works

### **3. Review Metrics Weekly**
```bash
# Monday morning routine
cashflowguard metrics --days 7
cashflowguard schedule --view-only
```

### **4. Personalize Messages**
- Use customer name
- Reference specific invoice
- Mention payment history if positive
- Offer help, not just demands

---

## 🔧 **Installation**

```bash
# Install required packages
pip install sqlite3 pandas

# Copy new modules to your project
cp message_generator.py cashflowguard/collections/
cp collections_scheduler.py cashflowguard/collections/
cp action_logger.py cashflowguard/core/

# Update CLI
# Add contents of cli_outreach.py to cashflowguard/cli.py
```

---

## 📚 **API Reference**

### **MessageGenerator**
- `generate_email()` - Create personalized email
- `generate_sms()` - Create SMS text (160 chars)
- `recommend_action()` - Suggest next best action

### **CollectionsScheduler**
- `generate_schedule()` - Create follow-up plan
- `get_todays_actions()` - Actions due today
- `get_this_weeks_actions()` - Weekly plan
- `reschedule_action()` - Modify schedule
- `mark_completed()` - Track completion
- `cancel_future_actions()` - Stop after payment

### **ActionLogger**
- `log_action()` - Record outreach
- `log_response()` - Track replies
- `log_outcome()` - Final result
- `get_invoice_history()` - Full timeline
- `calculate_success_metrics()` - Performance stats
- `export_audit_log()` - CSV export

---

## 🎊 **You Now Have:**

✅ **Personalized messaging** for every scenario  
✅ **Automated scheduling** based on risk  
✅ **Complete audit trail** in SQLite  
✅ **Success metrics** to optimize strategy  
✅ **Production-ready** collections automation  

**Your SMB collections tool is COMPLETE!** 🚀