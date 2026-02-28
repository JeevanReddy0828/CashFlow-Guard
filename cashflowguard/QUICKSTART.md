# CashFlowGuard Quickstart

## Setup (5 minutes)

```bash
# 1. Install dependencies
pip install -e . --break-system-packages

# 2. Generate sample data
python scripts/generate_synthetic_data.py --customers 50 --invoices 200 --months 6

# 3. Validate data
python -m cashflowguard.cli validate --data-dir data/sample
```

## Core Commands

### 1. Analyze AR
```bash
python -m cashflowguard.cli analyze --data-dir data/sample
```

### 2. Score Invoices (Fallback without ML)
```bash
python -m cashflowguard.cli score --data-dir data/sample
```

###  3. Generate Collections Plan
```bash
python -m cashflowguard.cli plan --data-dir data/sample --top 20 --tone friendly
```

### 4. Cash Flow Simulation
```bash
python -m cashflowguard.cli simulate --data-dir data/sample --scenarios 100 --days 30
```

### 5. Train ML Model (if you have payment history)
```bash
python -m cashflowguard.cli train --data-dir data/sample --model-dir models/
```

### 6. Record Actions
```bash
python -m cashflowguard.cli action \
  --invoice INV-00001 \
  --type reminder1 \
  --notes "Sent friendly reminder via email"
```

## Output Files

All outputs go to `outputs/` directory:
- `outputs/reports/` - Analysis reports
- `outputs/messages/` - Generated email/SMS templates  
- `outputs/plans/` - Collections plans

## Next Steps

1. Replace sample data with your actual invoices
2. Train ML model on historical payment data
3. Set up weekly cron job for collections plan
4. Integrate with your email system

## Help

```bash
python -m cashflowguard.cli --help
python -m cashflowguard.cli analyze --help
```
