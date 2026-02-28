# 💰 CashFlowGuard - Invoice Collections Management System

**Production-Ready Invoice Collections & Cash Flow Management Platform**

> A comprehensive system to help small businesses reduce late payments through machine learning, automated outreach, and intelligent collections scheduling.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0+-green.svg)](https://pandas.pydata.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![ML](https://img.shields.io/badge/ML-Gradient_Boost-orange.svg)](https://scikit-learn.org/)

---

## 🎯 **Overview**

CashFlowGuard is a complete invoice collections management system that helps businesses:

✅ **Track invoices** - CSV import with data validation  
✅ **Predict late payments** - ML model with 67% accuracy  
✅ **Prioritize collections** - Risk-based scoring system  
✅ **Generate outreach** - Personalized email and SMS templates  
✅ **Automate scheduling** - Smart follow-up cadences  
✅ **Track actions** - Complete audit trail in SQLite  
✅ **Visualize data** - Interactive dashboard  
✅ **Analyze metrics** - DSO, CEI, aging, forecasting  

### **Performance**
- Tested on **18,532 real invoices** from UCI Online Retail Dataset
- **67% test accuracy** on late payment prediction
- **15x performance improvement** through optimization
- Processes 18K+ invoices in under 2 seconds

---

## 📋 **Table of Contents**

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Core Features](#core-features)
4. [CLI Commands](#cli-commands)
5. [Dashboard](#dashboard)
6. [Data Format](#data-format)
7. [Project Structure](#project-structure)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)

---

## 📦 **Installation**

### **Requirements**
- Python 3.11+
- ~1GB disk space
- Windows/Linux/macOS

### **Setup**

**Windows:**

```powershell
# Create virtual environment
python -m venv venv
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r cashflowguard/requirements.txt

# Create required __init__.py files
New-Item -Path "cashflowguard\collections\__init__.py" -ItemType File -Force
New-Item -Path "cashflowguard\core\__init__.py" -ItemType File -Force
New-Item -Path "cashflowguard\ml\__init__.py" -ItemType File -Force
New-Item -Path "cashflowguard\analytics\__init__.py" -ItemType File -Force
```

**Linux/Mac:**

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r cashflowguard/requirements.txt
```

### **Dependencies**

```
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
typer>=0.9.0
rich>=13.0.0
pydantic>=2.0.0
streamlit>=1.28.0
plotly>=5.17.0
python-dateutil>=2.8.0
```

---

## 🚀 **Quick Start**

```bash
# 1. Validate your data
cashflowguard validate --data-dir data/sample

# 2. Train the ML model
cashflowguard train --data-dir data/sample --model-dir models

# 3. Score invoices for risk
cashflowguard score --data-dir data/sample

# 4. Generate collections plan
cashflowguard plan --data-dir data/sample --top 20

# 5. Launch dashboard
streamlit run dashboard.py
```

---

## ✨ **Core Features**

### **1. Invoice Risk Prediction**

Machine learning model that predicts late payment probability:

- **Algorithm**: Gradient Boosting Classifier
- **Features**: 25+ engineered features including customer history, payment patterns, temporal factors
- **Performance**: 67% accuracy on real test data
- **Output**: Risk score (0-100) and category (Low/Medium/High/Very High)

```bash
cashflowguard score --data-dir data/uci
```

### **2. AR Analytics**

Comprehensive accounts receivable metrics:

- **DSO**: Days Sales Outstanding
- **CEI**: Collection Effectiveness Index  
- **Aging**: 5-bucket analysis (Current, 1-30, 31-60, 61-90, 90+ days)
- **Forecasting**: Monte Carlo cash flow simulation

```bash
cashflowguard analyze --data-dir data/uci
cashflowguard simulate --scenarios 100 --days 30
```

### **3. Collections Planning**

Intelligent prioritization system:

- **Scoring**: Risk score × Invoice amount
- **Actions**: 6 escalation levels (Reminder → Call → Payment Plan → Escalate)
- **Weekly Plans**: Auto-generated action lists

```bash
cashflowguard plan --data-dir data/uci --top 50
```

### **4. Personalized Outreach**

Template generation system:

- **Email Templates**: 6 types from friendly to escalation
- **SMS Templates**: All under 160 characters
- **Personalization**: Customer name, amount, days overdue, payment history

```bash
python outreach_standalone.py
```

### **5. Automated Scheduling**

Risk-based follow-up system:

| Risk Level | Cadence (Days) | Duration |
|-----------|----------------|----------|
| Low | 7, 14, 21, 30 | 30 days |
| Medium | 5, 10, 15, 22, 30 | 30 days |
| High | 3, 7, 10, 14, 17, 21 | 21 days |
| Very High | 1, 3, 5, 7, 9, 12, 15 | 15 days |

### **6. Action Logging**

SQLite-based audit system tracking:
- All outreach actions (email, call, SMS)
- Customer responses
- Payment outcomes
- Success metrics by action type

---

## 🖥️ **CLI Commands**

### **Core Operations**

```bash
# Data validation
cashflowguard validate --data-dir <path>

# Risk scoring
cashflowguard score --data-dir <path>

# Collections planning
cashflowguard plan --data-dir <path> --top <n>

# AR analysis
cashflowguard analyze --data-dir <path>

# Cash flow simulation
cashflowguard simulate --data-dir <path> --scenarios 100 --days 30

# Model training
cashflowguard train --data-dir <path> --model-dir <path>
```

### **Tracking & Metrics**

```bash
# View action history
cashflowguard track view --invoice-id INV001

# Export audit log
cashflowguard track export --output audit.csv

# View success metrics
cashflowguard metrics --days 30
```

---

## 📊 **Dashboard**

### **Launch**

```bash
streamlit run dashboard.py
# Opens at http://localhost:8501
```

### **Features**

**Tab 1: Overview**
- Key metrics (Total AR, Overdue AR, DSO, Collection Rate)
- AR aging distribution
- Payment trends
- KPI summary

**Tab 2: Invoices**
- Searchable invoice list
- Advanced filtering
- CSV export

**Tab 3: Analytics**
- Customer concentration
- Status distribution
- Volume/value timeline

**Tab 4: Customers**
- Top customers by AR
- Credit utilization
- Concentration risk analysis

**Tab 5: Outreach**
- Message generation
- Template preview
- Bulk download

**Tab 6: Schedule**
- Cadence rules
- Weekly action plans
- Schedule export

---

## 📁 **Data Format**

### **Required CSV Files**

**customers.csv**
```csv
customer_id,name,email,payment_terms_days,credit_limit
CUST001,Acme Corp,john@acme.com,30,50000
```

**invoices.csv**
```csv
invoice_id,customer_id,invoice_amount,issue_date,due_date,status
INV001,CUST001,5000.00,2024-01-01,2024-01-31,open
```

**payments.csv**
```csv
payment_id,invoice_id,payment_date,amount,method,status
PAY001,INV002,2024-02-10,2500.00,bank_transfer,completed
```

### **Test Data**

The system includes sample data and was tested on the UCI Online Retail Dataset:
- **Source**: UK online retailer (2010-2011)
- **Scale**: 18,532 invoices, 4,338 customers, 17,612 payments
- **Geography**: 38 countries

---

## 🗂️ **Project Structure**

```
cashflowguard/
├── cashflowguard/
│   ├── cli.py                      # Main CLI
│   ├── config.py                   # Configuration
│   │
│   ├── core/
│   │   ├── loader.py               # Data loading
│   │   ├── validator.py            # Validation
│   │   └── action_logger.py        # Audit trail
│   │
│   ├── ml/
│   │   ├── features.py             # Feature engineering
│   │   ├── predict.py              # Risk scoring
│   │   └── train.py                # Model training
│   │
│   ├── analytics/
│   │   ├── ar_metrics.py           # DSO, CEI
│   │   ├── aging.py                # Aging analysis
│   │   └── forecasting.py          # Simulation
│   │
│   └── collections/
│       ├── planner.py              # Prioritization
│       ├── message_generator.py    # Templates
│       └── collections_scheduler.py # Scheduling
│
├── data/
│   ├── uci/                        # Real dataset
│   ├── real/                       # Synthetic B2B
│   └── sample/                     # Test data
│
├── models/
│   └── model_gradient_boost.pkl
│
├── dashboard.py                    # Streamlit app
├── outreach_standalone.py          # Message generator
└── README.md
```

---

## ⚙️ **Configuration**

### **Company Settings**

Edit `outreach_standalone.py`:

```python
DATA_DIR = "data/uci"
TOP_N = 20
ACTION_TYPE = "friendly_reminder"
COMPANY_NAME = "Your Company"
```

### **Risk Thresholds**

Edit `ml/predict.py`:

```python
RISK_THRESHOLDS = {
    "low": (0, 30),
    "medium": (31, 60),
    "high": (61, 85),
    "very_high": (86, 100)
}
```

### **Cadences**

Edit `collections/collections_scheduler.py`:

```python
CADENCES = {
    "low_risk": [7, 14, 21, 30],
    "medium_risk": [5, 10, 15, 22, 30],
    "high_risk": [3, 7, 10, 14, 17, 21],
    "very_high_risk": [1, 3, 5, 7, 9, 12, 15]
}
```

---

## 🔧 **Troubleshooting**

### **Module Import Errors**

```bash
# Ensure __init__.py files exist
touch cashflowguard/collections/__init__.py
touch cashflowguard/core/__init__.py
touch cashflowguard/ml/__init__.py

# Test imports
python -c "from cashflowguard.collections.message_generator import MessageGenerator"
```

### **Dashboard Missing Tabs**

1. Verify enhanced dashboard version
2. Check module imports work
3. Restart Streamlit

### **Date Parsing Issues**

Always use pandas datetime conversion:

```python
df["date_col"] = pd.to_datetime(df["date_col"], errors='coerce')
```

### **Performance Issues**

Use vectorized operations:

```python
# Fast
df["days"] = (df["end_date"] - df["start_date"]).dt.days

# Slow
df["days"] = df.apply(lambda row: (row["end"] - row["start"]).days, axis=1)
```

---

## 📈 **Performance Metrics**

- Process 18K invoices: < 2 seconds
- Train ML model: < 15 seconds
- Generate 100 emails: < 1 second
- Dashboard load: < 3 seconds

**Optimization techniques:**
- Vectorized pandas operations
- Efficient date parsing
- Streamlit caching
- Batch processing

---

## 🎯 **Roadmap**

### **Completed**
- [x] Invoice tracking and validation
- [x] ML risk prediction
- [x] Collections prioritization
- [x] Email/SMS templates
- [x] Automated scheduling
- [x] Action logging
- [x] Interactive dashboard
- [x] CLI interface

### **Planned**
- [ ] QuickBooks integration
- [ ] SMTP email sending
- [ ] SMS integration (Twilio)
- [ ] Multi-currency support
- [ ] API endpoints
- [ ] Mobile app

---

## 📊 **Project Statistics**

```
Lines of Code:      ~8,000
Python Files:       25+
ML Features:        25+
Email Templates:    6
CLI Commands:       10
Dashboard Tabs:     6
Test Invoices:      18,532
Customers:          4,338
Performance Gain:   15x
```

---

## 📄 **License**

MIT License

---

## 🙏 **Acknowledgments**

- UCI Machine Learning Repository - Online Retail Dataset
- Scikit-learn - ML framework
- Pandas - Data processing
- Streamlit - Dashboard
- Plotly - Visualizations

---

**Built for small businesses fighting late payments**

*Version 1.0.0*  
*Updated: February 2026*