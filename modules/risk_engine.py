"""Risk scoring engine for audit findings."""

from __future__ import annotations

import pandas as pd


def score_level(score: float) -> str:
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def reconciliation_risk(unmatched_count: int, long_pending: int, total: int) -> float:
    if total == 0:
        return 0.0
    return min(100, (unmatched_count / total) * 60 + (long_pending / total) * 40)


def round_trip_risk(suspicious_count: int, total: int, related_party_pct: float) -> float:
    if total == 0:
        return 0.0
    base = (suspicious_count / total) * 70
    return min(100, base + related_party_pct * 30)


def charges_risk(excess_count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return min(100, (excess_count / total) * 100)


def idle_balance_risk(idle_total: float, total_balance: float) -> float:
    if total_balance == 0:
        return 0.0
    ratio = idle_total / total_balance
    return min(100, ratio * 100)


def authorization_risk(unauthorized: int, duplicates: int, total: int) -> float:
    if total == 0:
        return 0.0
    return min(100, (unauthorized / total) * 60 + (duplicates / total) * 40)


def composite_risk(scores: dict[str, float]) -> float:
    if not scores:
        return 0.0
    weights = {
        "reconciliation": 0.25,
        "round_trip": 0.25,
        "charges": 0.15,
        "idle_balance": 0.15,
        "authorization": 0.20,
    }
    total_w = sum(weights.get(k, 0.1) for k in scores)
    return sum(scores[k] * weights.get(k, 0.1) for k in scores) / total_w


def generate_exception_summary(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for module, df in results.items():
        if df is not None and not df.empty and "Risk Level" in df.columns:
            for level in ["High", "Medium", "Low"]:
                count = (df["Risk Level"] == level).sum()
                if count:
                    rows.append({"Module": module, "Risk Level": level, "Count": count})
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Module", "Risk Level", "Count"])
