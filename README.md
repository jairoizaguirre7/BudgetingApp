# BudgetingApp
# BudgetingApp
# BudgetingApp
# BudgetingApp
# Budgeting App

A simple Flask budgeting application that supports **manual CSV upload** and computes budget summaries.

## Features
- Upload transactions via CSV
- Basic category inference if category is omitted
- Budget summary totals (income, expenses, net)
- Breakdown by category and month
- Persisted transaction history in `data/transactions.json`
- Configurable storage path via `BUDGET_DATA_FILE`

## CSV format
Required columns:
- `date` (`YYYY-MM-DD`, `MM/DD/YYYY`, or `DD-MM-YYYY`)
- `description`
- `amount` (positive = income, negative = expense)

Optional column:
- `category`

`amount` supports values such as `1500`, `-85.20`, `"$1,250.00"`, and `(1200)`. UTF-8 BOM-prefixed CSV headers are also accepted.

Example:

```csv
date,description,amount,category
2025-01-01,Salary,3000,Income
2025-01-02,Grocery Store,-85.20,Groceries
```

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000`.

## Run tests
```bash
pytest
```
