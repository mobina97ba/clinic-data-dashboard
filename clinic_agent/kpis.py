"""Deterministic KPI calculations. All business maths lives here."""
from __future__ import annotations

import pandas as pd

from .config import GROUP_LABELS


def _div(a: float, b: float) -> float:
    return float(a) / float(b) if b else 0.0


def summarise(df: pd.DataFrame) -> dict:
    """KPIs for any slice of cleaned data."""
    n = len(df)
    done = df[df["status_group"] == "completed"]
    cancelled = int((df["status_group"] == "cancelled").sum())
    no_show = int((df["status_group"] == "no_show").sum())
    billed = float(done["billed_amount"].sum())
    collected = float(done["collected_amount"].sum())
    # Per-visit shortfall, so an overpayment on one visit cannot hide an unpaid one.
    shortfall = (done["billed_amount"] - done["collected_amount"]).clip(lower=0)
    return {
        "appointments": n,
        "completed": len(done),
        "cancelled": cancelled,
        "no_show": no_show,
        "other": n - len(done) - cancelled - no_show,
        "completion_rate": _div(len(done), n),
        "cancel_rate": _div(cancelled, n),
        "no_show_rate": _div(no_show, n),
        "lost_rate": _div(cancelled + no_show, n),
        "billed": billed,
        "collected": collected,
        "outstanding": float(shortfall.sum()),
        "unpaid_visits": int((shortfall > 0).sum()),
        "collection_rate": _div(collected, billed),
        "avg_billed": _div(billed, len(done)),
    }


def by_dimension(df: pd.DataFrame, column: str, sort_by: str = "billed",
                 ascending: bool = False) -> pd.DataFrame:
    rows = [{column: key, **summarise(g)} for key, g in df.groupby(column, dropna=False)]
    out = pd.DataFrame(rows)
    return out if out.empty else out.sort_values(sort_by, ascending=ascending).reset_index(drop=True)


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    return by_dimension(df, "month", sort_by="month", ascending=True)


def status_counts(df: pd.DataFrame) -> pd.DataFrame:
    counts = df["status_group"].map(GROUP_LABELS).value_counts()
    return counts.rename_axis("status").reset_index(name="appointments")


def repeat_patients(df: pd.DataFrame) -> dict | None:
    """Share of patients with 2+ completed visits. None if no patient IDs."""
    done = df[(df["status_group"] == "completed") & df["patient_id"].notna()]
    if done.empty:
        return None
    visits = done.groupby("patient_id").size()
    return {"patients": int(len(visits)), "repeat": int((visits >= 2).sum()),
            "rate": _div((visits >= 2).sum(), len(visits))}


def filter_data(df: pd.DataFrame, clinics=None, sources=None, start=None, end=None) -> pd.DataFrame:
    out = df
    if clinics is not None:
        out = out[out["clinic"].isin(clinics)]
    if sources is not None:
        out = out[out["marketing_source"].isin(sources)]
    if start is not None:
        out = out[out["appointment_date"].dt.date >= start]
    if end is not None:
        out = out[out["appointment_date"].dt.date <= end]
    return out
