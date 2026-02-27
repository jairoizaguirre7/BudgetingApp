from __future__ import annotations

import csv
import io
import json
import os
from json import JSONDecodeError
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
BASE_DIR = Path(__file__).parent
DEFAULT_DATA_FILE = BASE_DIR / "data" / "transactions.json"
app.config["DATA_FILE"] = Path(os.getenv("BUDGET_DATA_FILE", DEFAULT_DATA_FILE))

REQUIRED_COLUMNS = {"date", "description", "amount"}


def _get_data_file() -> Path:
    return Path(app.config["DATA_FILE"])


def _load_transactions() -> list[dict[str, Any]]:
    data_file = _get_data_file()
    if not data_file.exists():
        return []

    with data_file.open("r", encoding="utf-8") as file:
        try:
            data = json.load(file)
        except JSONDecodeError:
            return []

    if not isinstance(data, list):
        return []
    return data


def _save_transactions(transactions: list[dict[str, Any]]) -> None:
    data_file = _get_data_file()
    data_file.parent.mkdir(parents=True, exist_ok=True)

    with data_file.open("w", encoding="utf-8") as file:
        json.dump(transactions, file, indent=2)


def _infer_category(description: str) -> str:
    lowered = description.lower()
    rules = {
        "Groceries": ["grocery", "market", "super"],
        "Transport": ["uber", "lyft", "gas", "train", "bus"],
        "Housing": ["rent", "mortgage", "utility"],
        "Dining": ["restaurant", "cafe", "coffee", "pizza"],
        "Income": ["salary", "payroll", "bonus", "refund"],
    }
    for category, keywords in rules.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "Other"


def _parse_date(value: str) -> str:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {value}")


def _parse_amount(value: str) -> float:
    normalized = value.strip().replace(",", "").replace("$", "")
    if normalized.startswith("(") and normalized.endswith(")"):
        normalized = f"-{normalized[1:-1]}"
    return float(normalized)


def parse_csv(content: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError("CSV is empty or missing a header row")

    headers = {header.strip().lower().lstrip("\ufeff") for header in reader.fieldnames if header}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    transactions: list[dict[str, Any]] = []
    for row_number, row in enumerate(reader, start=2):
        if not row:
            continue

        normalized_row = {(key or "").strip().lower().lstrip("\ufeff"): (value or "").strip() for key, value in row.items()}
        if not any(normalized_row.values()):
            continue

        try:
            date = _parse_date(normalized_row["date"])
            description = normalized_row["description"]
            if not description:
                raise ValueError("Description cannot be empty")
            amount = _parse_amount(normalized_row["amount"])
            category = normalized_row.get("category") or _infer_category(description)
        except KeyError as error:
            raise ValueError(f"Missing required field {error.args[0]} on row {row_number}") from error
        except ValueError as error:
            raise ValueError(f"Invalid row {row_number}: {error}") from error

        transactions.append(
            {
                "date": date,
                "description": description,
                "amount": amount,
                "category": category,
                "month": date[:7],
            }
        )

    if not transactions:
        raise ValueError("No transaction rows found in CSV")

    return transactions


def build_summary(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    total_income = 0.0
    total_expenses = 0.0
    by_category: dict[str, float] = {}
    by_month: dict[str, float] = {}

    for item in transactions:
        amount = float(item["amount"])
        if amount >= 0:
            total_income += amount
        else:
            total_expenses += abs(amount)

        category = item["category"]
        by_category[category] = by_category.get(category, 0.0) + amount

        month = item["month"]
        by_month[month] = by_month.get(month, 0.0) + amount

    return {
        "totals": {
            "income": round(total_income, 2),
            "expenses": round(total_expenses, 2),
            "net": round(total_income - total_expenses, 2),
        },
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items())},
        "by_month": {k: round(v, 2) for k, v in sorted(by_month.items())},
    }


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.post("/upload")
def upload() -> Any:
    file = request.files.get("file")
    if file is None or file.filename == "":
        return jsonify({"error": "Please upload a CSV file"}), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only .csv files are supported"}), 400

    content = file.read().decode("utf-8", errors="ignore")
    if not content.strip():
        return jsonify({"error": "Uploaded file is empty"}), 400

    try:
        uploaded_transactions = parse_csv(content)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    all_transactions = _load_transactions() + uploaded_transactions
    _save_transactions(all_transactions)
    return jsonify({"transactions": uploaded_transactions, "summary": build_summary(all_transactions)})


@app.get("/summary")
def summary() -> Any:
    transactions = _load_transactions()
    return jsonify({"transactions": transactions, "summary": build_summary(transactions)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
