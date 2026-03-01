# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project layout

The repo has a nested structure. The installable Python package lives inside a subdirectory of the same name:

```
cashflowguard-with-uci-adapter/   ← git root
└── cashflowguard/                ← project root (run all commands from here)
    ├── cashflowguard/            ← Python package source
    ├── dashboard.py
    ├── outreach_standalone.py
    ├── data/{sample,UCI,real}/
    ├── models/                   ← pickle artifacts written here
    ├── outputs/{messages,reports,plans}/
    └── scripts/
```

**All commands below must be run from `cashflowguard/` (the inner project root), not the git root.**

## Commands

```bash
# Install (editable + dev extras)
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_validators.py -v

# Validate input CSVs
cashflowguard validate --data-dir data/sample

# Train the ML model
cashflowguard train --data-dir data/sample --model-dir models

# Score open invoices for risk
cashflowguard score --data-dir data/sample

# Generate a collections action plan
cashflowguard plan --data-dir data/sample --top 20

# Run AR analytics
cashflowguard analyze --data-dir data/sample

# Cash flow Monte Carlo simulation
cashflowguard simulate --data-dir data/sample --scenarios 100 --days 30

# Generate outreach messages
python outreach_standalone.py
# or via CLI:
cashflowguard outreach --data-dir data/uci --top 20 --action-type second_notice

# Launch Streamlit dashboard
streamlit run dashboard.py

# Generate synthetic test data
python scripts/generate_synthetic_data.py --customers 50 --invoices 200 --months 6

# Transform UCI Online Retail dataset → internal CSV format
python scripts/transform_uci_data.py

# Clean build artifacts and outputs
make clean
```

## Architecture

### Data flow

```
CSV input (customers / invoices / payments)
  → io/loaders.py (DataLoader)         load + optionally validate
  → io/validators.py                   schema + referential integrity checks
  → ml/features.py engineer_features() build 25 features (vectorized)
  → ml/train.py   LatePaymentModel     train GradientBoost, time-based split, cross-val, pickle
  → ml/predict.py score_invoices()     load pickle → predict_proba → risk score 0-100
  → recommendations/engine.py          prioritized action list
  → collections/message_generator.py  Jinja2 email/SMS outreach
  → collections/collections_scheduler.py  risk-tiered follow-up cadence
  → core/action_logger.py             SQLite audit trail (collections_audit.db)
  → outputs/
```

### Key design decisions

**ML pipeline**
- `engineer_features()` is called both during training and inference — keep them in sync.
- Training uses a **time-based split** (sort by `issue_date`, oldest 75% = train), not random split, to prevent leakage.
- The `StandardScaler` is bundled with the model in the same pickle so inference always uses the training-time scaler.
- `score_invoices()` falls back to a weighted rule-based scorer (40% overdue, 20% amount, 20% terms, 20% utilization) if no model file is found.

**Feature engineering**
- All date operations use `pd.to_datetime(..., errors='coerce')` + vectorized `.dt` accessors — never row-wise `apply()`.
- New customers with no payment history get conservative defaults (`late_rate=0`, `avg_days_late=0`) rather than errors.
- The 3 interaction features (`amount_x_days_until_due`, `amount_x_late_rate`, `utilization_x_late_rate`) capture non-linear relationships between amount, timing, and customer behavior.

**Config**
- A single Pydantic `Config` model (`cashflowguard/config.py`) owns all tunable parameters: paths, ML hyperparameters, escalation schedule (`[3, 10, 20, 45, 90]` days), risk thresholds.
- `config.ensure_directories()` must be called before writing outputs.

**Collections outreach**
- Outreach tones (friendly / neutral / firm) map to Jinja2 templates in `cashflowguard/templates/`.
- `cli_outreach.py` defines a standalone Typer app that is *separate* from the main `cli.py` — it is not yet wired into the main `cashflowguard` entry point.

**Persistence**
- Trained models → `models/*.pkl` (pickle of dict containing `model`, `scaler`, `feature_columns`, `feature_importances`).
- Action audit trail → `collections_audit.db` (SQLite, managed by `core/action_logger.py`).

## Input data schema

```
customers.csv  : customer_id, name, email, payment_terms_days, credit_limit
invoices.csv   : invoice_id, customer_id, invoice_amount, issue_date, due_date, status
payments.csv   : payment_id, invoice_id, payment_date, amount, method, status
```

`status` on invoices must be `"open"` for an invoice to be scored and included in collections planning.

## Risk categories

| Score | Category |
|---|---|
| 0–30 | low |
| 31–60 | medium |
| 61–85 | high |
| 86–100 | very_high |

Collections cadence (days after issue): low → [7,14,21,30], medium → [5,10,15,22,30], high → [3,7,10,14,17,21], very_high → [1,3,5,7,9,12,15].
