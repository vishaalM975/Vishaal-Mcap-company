"""Data loading, sample data generation, and Excel/CSV import utilities."""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


def _rng(seed: int = 42) -> np.random.Generator:
    return np.random.default_rng(seed)


def generate_reconciliation_data(n: int = 120) -> pd.DataFrame:
    rng = _rng()
    base = datetime(2025, 1, 1)
    dates = [base + timedelta(days=int(d)) for d in rng.integers(0, 180, n)]
    statuses = ["Matched", "Unmatched", "Partial", "Pending Review"]
    bank_statuses = ["Cleared", "Pending", "Returned", "On Hold"]
    ledger_statuses = ["Posted", "Pending", "Reversed", "Not Found"]

    rows = []
    for i in range(n):
        rec_status = rng.choice(statuses, p=[0.45, 0.25, 0.15, 0.15])
        rows.append({
            "Date": dates[i],
            "Transaction ID": f"TXN-{10000 + i:05d}",
            "Amount": round(rng.uniform(500, 250000), 2),
            "Bank Status": rng.choice(bank_statuses),
            "Ledger Status": rng.choice(ledger_statuses),
            "Reconciliation Status": rec_status,
        })

    # Guaranteed long-pending unmatched items for demo aging charts
    for i, days_ago in enumerate([95, 102, 115, 130, 145]):
        rows.append({
            "Date": datetime.now() - timedelta(days=days_ago),
            "Transaction ID": f"TXN-DEMO-{9000 + i}",
            "Amount": round(rng.uniform(75000, 500000), 2),
            "Bank Status": "Pending",
            "Ledger Status": "Not Found",
            "Reconciliation Status": "Unmatched",
        })
    return pd.DataFrame(rows)


def generate_transfer_data(n: int = 80) -> pd.DataFrame:
    rng = _rng(7)
    accounts = [f"ACC-{1000 + i}" for i in range(12)]
    base = datetime(2025, 3, 1)
    rows = []
    for i in range(n):
        frm, to = rng.choice(accounts, 2, replace=False)
        amt = round(rng.choice([50000, 100000, 250000, 500000, 1000000]) * rng.uniform(0.95, 1.05), 2)
        rows.append({
            "From Account": frm,
            "To Account": to,
            "Amount": amt,
            "Date": base + timedelta(days=int(rng.integers(0, 90)), hours=int(rng.integers(0, 23))),
            "Related Party Flag": rng.choice(["Yes", "No"], p=[0.25, 0.75]),
        })
    # Inject round-trip patterns
    for _ in range(5):
        a, b = rng.choice(accounts, 2, replace=False)
        amt = round(rng.uniform(100000, 500000), 2)
        d = base + timedelta(days=int(rng.integers(10, 60)))
        rows.append({"From Account": a, "To Account": b, "Amount": amt, "Date": d, "Related Party Flag": "Yes"})
        rows.append({"From Account": b, "To Account": a, "Amount": amt, "Date": d + timedelta(days=2), "Related Party Flag": "Yes"})
    return pd.DataFrame(rows)


def generate_charges_data(n: int = 40) -> pd.DataFrame:
    rng = _rng(13)
    rows = []
    for i in range(n):
        loan = round(rng.uniform(500000, 10000000), 2)
        rate = round(rng.uniform(7.5, 12.5), 2)
        tenure = int(rng.choice([12, 24, 36, 48, 60]))
        expected_interest = round(loan * (rate / 100) * (tenure / 12), 2)
        proc_fee = round(loan * 0.01, 2)
        variance = rng.choice([-1, 0, 1, 1], p=[0.15, 0.5, 0.2, 0.15])
        actual = expected_interest + proc_fee + variance * rng.uniform(5000, 50000)
        rows.append({
            "Loan Amount": loan,
            "Interest Rate": rate,
            "Charges": proc_fee,
            "Tenure": tenure,
            "Actual Debit": round(actual, 2),
            "Account ID": f"LN-{2000 + i}",
        })
    return pd.DataFrame(rows)


def generate_idle_balance_data(n: int = 30) -> pd.DataFrame:
    rng = _rng(21)
    rows = []
    base = datetime(2025, 5, 1)
    for i in range(n):
        threshold = round(rng.uniform(100000, 500000), 2)
        balance = round(rng.uniform(threshold * 0.5, threshold * 3), 2)
        rows.append({
            "Account Number": f"ACC-{3000 + i}",
            "Daily Balance": balance,
            "Sweep Threshold": threshold,
            "Interest Rate": round(rng.uniform(4.0, 7.5), 2),
            "Date": base + timedelta(days=int(rng.integers(0, 30))),
        })
    return pd.DataFrame(rows)


def generate_authorization_data(n: int = 60) -> pd.DataFrame:
    rng = _rng(33)
    signatories = ["J. Smith", "A. Patel", "R. Kumar", "M. Chen", "S. Williams"]
    unauthorized = ["T. Brown", "Guest User", "System Auto", "Unknown"]
    rows = []
    for i in range(n):
        auth_list = ", ".join(rng.choice(signatories, size=rng.integers(2, 4), replace=False))
        is_bad = rng.random() < 0.18
        approver = rng.choice(unauthorized if is_bad else signatories)
        rows.append({
            "Transaction ID": f"APV-{5000 + i:05d}",
            "Approved By": approver,
            "Authorized List": auth_list,
            "Approval Timestamp": datetime(2025, 4, 1) + timedelta(
                days=int(rng.integers(0, 60)), hours=int(rng.integers(8, 18))
            ),
            "Amount": round(rng.uniform(10000, 2000000), 2),
        })
    return pd.DataFrame(rows)


def generate_bank_rent_data(n: int = 24) -> pd.DataFrame:
    """Monthly bank rent and service charges across accounts."""
    rng = _rng(44)
    banks = ["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Mahindra"]
    charge_types = ["Locker Rent", "Min Balance Penalty", "SMS Alerts", "Cheque Book", "Annual Maintenance"]
    rows = []
    for i in range(n):
        sanctioned = round(rng.uniform(200, 5000), 2)
        variance = rng.choice([0, 0, 1, -1], p=[0.5, 0.2, 0.2, 0.1])
        actual = max(0, sanctioned + variance * rng.uniform(100, 2000))
        rows.append({
            "Account Number": f"ACC-{5000 + i % 8}",
            "Bank Name": rng.choice(banks),
            "Charge Type": rng.choice(charge_types),
            "Sanctioned Amount": sanctioned,
            "Actual Charge": round(actual, 2),
            "Month": datetime(2025, 1, 1) + timedelta(days=30 * (i // 5)),
            "Flag": "Excess" if actual > sanctioned * 1.05 else "OK",
        })
    return pd.DataFrame(rows)


def generate_money_spending_details(n: int = 100) -> pd.DataFrame:
    """Line-level spending for drill-down analytics."""
    rng = _rng(55)
    categories = ["Payroll", "Vendor Payments", "Utilities", "Rent", "IT Services",
                  "Marketing", "Travel", "Insurance", "Taxes", "Miscellaneous"]
    merchants = ["Amazon Web Services", "Office Lease Co", "PowerGrid Ltd", "TCS", "Deloitte",
                   "MakeMyTrip", "LIC Premium", "GST Payment", "Staff Salaries", "Misc Vendor"]
    base = datetime(2025, 1, 1)
    rows = []
    for i in range(n):
        rows.append({
            "Date": base + timedelta(days=int(rng.integers(0, 180))),
            "Description": rng.choice(merchants),
            "Category": rng.choice(categories),
            "Amount": round(rng.uniform(5000, 350000), 2),
            "Account Number": f"ACC-{4000 + rng.integers(0, 15)}",
            "Payment Mode": rng.choice(["NEFT", "RTGS", "UPI", "Cheque", "Auto-Debit"]),
        })
    return pd.DataFrame(rows)


def generate_monthly_trends() -> pd.DataFrame:
    """Monthly bank balance and transaction trends."""
    rng = _rng(61)
    months = pd.date_range("2024-07-01", periods=12, freq="MS")
    return pd.DataFrame({
        "Month": months,
        "Avg Daily Balance": np.round(rng.uniform(5000000, 25000000, 12), 2),
        "Transaction Count": rng.integers(800, 3500, 12),
        "Bank Charges": np.round(rng.uniform(15000, 85000, 12), 2),
        "Interest Earned": np.round(rng.uniform(80000, 450000, 12), 2),
    })

def generate_cashflow_data(n: int = 12) -> pd.DataFrame:
    rng = _rng(55)
    months = pd.date_range("2024-07-01", periods=n, freq="MS")
    inflow = rng.uniform(2000000, 5000000, n)
    outflow = inflow * rng.uniform(0.7, 1.1, n)
    return pd.DataFrame({
        "Month": months,
        "Inflow": np.round(inflow, 2),
        "Outflow": np.round(outflow, 2),
        "Net Cash Flow": np.round(inflow - outflow, 2),
    })


def generate_spending_data() -> pd.DataFrame:
    categories = ["Payroll", "Vendor Payments", "Utilities", "Rent", "IT Services",
                  "Marketing", "Travel", "Insurance", "Taxes", "Miscellaneous"]
    rng = _rng(66)
    amounts = rng.uniform(50000, 800000, len(categories))
    return pd.DataFrame({"Category": categories, "Amount": np.round(amounts, 2)})


def generate_vendor_payments(n: int = 25) -> pd.DataFrame:
    rng = _rng(77)
    vendors = [f"Vendor-{chr(65 + i)}" for i in range(n)]
    return pd.DataFrame({
        "Vendor": vendors,
        "Amount": np.round(rng.uniform(10000, 500000, n), 2),
        "Payment Date": [datetime(2025, 1, 1) + timedelta(days=int(d)) for d in rng.integers(0, 180, n)],
        "Status": rng.choice(["Paid", "Pending", "Overdue"], n, p=[0.7, 0.2, 0.1]),
    })


def generate_account_details(n: int = 15) -> pd.DataFrame:
    banks = ["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Mahindra"]
    types = ["Current", "Savings", "Fixed Deposit", "Overdraft"]
    rng = _rng(88)
    return pd.DataFrame({
        "Account Number": [f"ACC-{4000 + i}" for i in range(n)],
        "Bank Name": rng.choice(banks, n),
        "Account Type": rng.choice(types, n),
        "Balance": np.round(rng.uniform(100000, 15000000, n), 2),
        "Currency": "INR",
        "Status": rng.choice(["Active", "Dormant", "Frozen"], n, p=[0.8, 0.15, 0.05]),
    })


def generate_transaction_frequency() -> pd.DataFrame:
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours = list(range(8, 20))
    rng = _rng(99)
    records = []
    for d in days:
        for h in hours:
            weight = 1.0 if d not in ("Sat", "Sun") else 0.3
            if 10 <= h <= 16:
                weight *= 1.5
            records.append({"Day": d, "Hour": h, "Count": int(rng.poisson(15 * weight))})
    return pd.DataFrame(records)


def get_all_sample_data() -> dict[str, pd.DataFrame]:
    """Return full dummy banking dataset — ready to explore every module without uploads."""
    return {
        "reconciliation": generate_reconciliation_data(),
        "transfers": generate_transfer_data(),
        "charges": generate_charges_data(),
        "idle_balance": generate_idle_balance_data(),
        "authorization": generate_authorization_data(),
        "cashflow": generate_cashflow_data(),
        "spending": generate_spending_data(),
        "vendors": generate_vendor_payments(),
        "accounts": generate_account_details(),
        "frequency": generate_transaction_frequency(),
        "bank_rent": generate_bank_rent_data(),
        "spending_details": generate_money_spending_details(),
        "monthly_trends": generate_monthly_trends(),
    }


def sample_data_summary(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Row counts per dataset for the demo-data sidebar."""
    return pd.DataFrame([
        {"Dataset": k.replace("_", " ").title(), "Records": len(v)}
        for k, v in data.items()
        if v is not None and not v.empty
    ])


_DATE_COLUMNS: dict[str, str] = {
    "reconciliation": "Date",
    "transfers": "Date",
    "idle_balance": "Date",
    "authorization": "Approval Timestamp",
    "vendors": "Payment Date",
    "cashflow": "Month",
    "bank_rent": "Month",
    "spending_details": "Date",
    "monthly_trends": "Month",
}


def apply_date_filters(
    data: dict[str, pd.DataFrame],
    start: datetime,
    end: datetime,
) -> dict[str, pd.DataFrame]:
    """Filter date-bearing datasets to the sidebar range; leave others unchanged."""
    filtered = {}
    for key, df in data.items():
        date_col = _DATE_COLUMNS.get(key)
        if date_col and date_col in df.columns:
            filtered[key] = filter_by_date_range(df, date_col, start, end)
        else:
            filtered[key] = df
    return filtered


def ensure_sample_excel(path: Path) -> Path:
    """Write bundled demo Excel workbook if missing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        data = get_all_sample_data()
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for name, df in data.items():
                df.to_excel(writer, sheet_name=name[:31], index=False)
    return path



def load_uploaded_file(uploaded_file) -> dict[str, pd.DataFrame]:
    """Load Excel or CSV upload; return dict of sheet_name -> DataFrame."""
    if uploaded_file is None:
        return {}

    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        return {"Sheet1": df}

    if name.endswith((".xlsx", ".xls")):
        xls = pd.ExcelFile(uploaded_file, engine="openpyxl")
        return {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names}

    return {}


def detect_dataset_type(df: pd.DataFrame) -> str | None:
    """Heuristic mapping of uploaded columns to module keys."""
    cols = {c.lower().strip() for c in df.columns}
    mappings = [
        ("reconciliation", {"reconciliation status", "bank status", "ledger status"}),
        ("transfers", {"from account", "to account", "related party flag"}),
        ("charges", {"loan amount", "interest rate", "tenure", "actual debit"}),
        ("idle_balance", {"daily balance", "sweep threshold"}),
        ("authorization", {"approved by", "authorized list", "approval timestamp"}),
        ("cashflow", {"inflow", "outflow", "net cash flow"}),
        ("spending", {"category", "amount"}),
        ("vendors", {"vendor", "payment date"}),
        ("accounts", {"bank name", "account type", "balance"}),
    ]
    for key, required in mappings:
        if required.issubset(cols):
            return key
    return None


def merge_uploaded_data(uploaded: dict[str, pd.DataFrame], sample: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Merge uploaded sheets into sample data, auto-detecting type."""
    result = sample.copy()
    for _sheet, df in uploaded.items():
        dtype = detect_dataset_type(df)
        if dtype:
            result[dtype] = df
        else:
            result[f"upload_{_sheet}"] = df
    return result


def to_excel_bytes(dfs: dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        for name, df in dfs.items():
            sheet = name[:31]
            df.to_excel(writer, sheet_name=sheet, index=False)
    return buffer.getvalue()


def filter_by_date_range(df: pd.DataFrame, date_col: str, start: datetime, end: datetime) -> pd.DataFrame:
    if date_col not in df.columns:
        return df
    col = pd.to_datetime(df[date_col], errors="coerce")
    return df[(col >= pd.Timestamp(start)) & (col <= pd.Timestamp(end))].copy()
