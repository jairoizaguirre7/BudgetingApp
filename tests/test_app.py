from io import BytesIO
from pathlib import Path

import pytest

from app import app, build_summary, parse_csv


@pytest.fixture(autouse=True)
def isolate_data_file(tmp_path: Path) -> None:
    app.config["DATA_FILE"] = tmp_path / "transactions.json"


def test_parse_csv_success() -> None:
    data = "date,description,amount,category\n2025-01-10,Salary,4500,Income\n2025-01-11,Coffee,-5,Dining\n"
    transactions = parse_csv(data)
    assert len(transactions) == 2
    assert transactions[0]["month"] == "2025-01"


def test_parse_csv_amount_formats() -> None:
    data = 'date,description,amount\n2025-01-10,Salary,"$1,500.25"\n2025-01-11,Rent,(1200)\n'
    transactions = parse_csv(data)
    assert transactions[0]["amount"] == 1500.25
    assert transactions[1]["amount"] == -1200.0




def test_parse_csv_with_bom_header() -> None:
    data = "\ufeffdate,description,amount\n2025-01-10,Salary,1000\n"
    transactions = parse_csv(data)
    assert transactions[0]["date"] == "2025-01-10"


def test_parse_csv_rejects_empty_description() -> None:
    data = "date,description,amount\n2025-01-10,,1000\n"
    with pytest.raises(ValueError, match="Description cannot be empty"):
        parse_csv(data)

def test_parse_csv_missing_column() -> None:
    data = "date,description\n2025-01-10,Salary\n"
    with pytest.raises(ValueError, match="Missing required columns"):
        parse_csv(data)


def test_build_summary() -> None:
    summary = build_summary(
        [
            {"date": "2025-01-10", "description": "Salary", "amount": 1000, "category": "Income", "month": "2025-01"},
            {"date": "2025-01-11", "description": "Groceries", "amount": -100, "category": "Groceries", "month": "2025-01"},
            {"date": "2025-02-12", "description": "Bus", "amount": -50, "category": "Transport", "month": "2025-02"},
        ]
    )
    assert summary["totals"] == {"income": 1000.0, "expenses": 150.0, "net": 850.0}
    assert summary["by_month"]["2025-01"] == 900.0


def test_upload_endpoint() -> None:
    client = app.test_client()
    data = {
        "file": (BytesIO(b"date,description,amount\n2025-01-10,Salary,1000\n"), "transactions.csv"),
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    payload = response.get_json()
    assert "summary" in payload


def test_upload_invalid_extension() -> None:
    client = app.test_client()
    data = {
        "file": (BytesIO(b"not,relevant\n"), "transactions.txt"),
    }
    response = client.post("/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 400


def test_summary_ignores_corrupt_storage_file(tmp_path: Path) -> None:
    bad_file = tmp_path / "transactions.json"
    bad_file.write_text("not-json", encoding="utf-8")
    app.config["DATA_FILE"] = bad_file

    client = app.test_client()
    response = client.get("/summary")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["transactions"] == []
    assert payload["summary"]["totals"]["net"] == 0.0
