"""Markdown management report."""
from __future__ import annotations

import pandas as pd

from .insights import money, pct


def _md_table(df: pd.DataFrame, columns: dict[str, str], fmt: dict) -> str:
    if df.empty:
        return "_No data._"
    head = "| " + " | ".join(columns.values()) + " |\n|" + "---|" * len(columns) + "\n"
    rows = ""
    for _, r in df.iterrows():
        rows += "| " + " | ".join(fmt.get(c, str)(r[c]) for c in columns) + " |\n"
    return head + rows


def build_report(source: str, k: dict, by_clinic: pd.DataFrame, by_source: pd.DataFrame,
                 insights: list[str], quality: dict) -> str:
    perf = {"appointments": "Appts", "completed": "Completed", "billed": "Billed",
            "collected": "Collected", "lost_rate": "Lost rate"}
    fmt = {"billed": money, "collected": money, "lost_rate": pct,
           "appointments": lambda v: f"{int(v):,}", "completed": lambda v: f"{int(v):,}"}
    lines = [
        "# Clinic Data Intelligence Report", "", f"Source: {source}", "",
        "## KPIs",
        f"- Appointments: {k['appointments']:,}",
        f"- Completed: {k['completed']:,} ({pct(k['completion_rate'])})",
        f"- Billed revenue: AUD {money(k['billed'])}",
        f"- Collections: AUD {money(k['collected'])} ({pct(k['collection_rate'])} of billed)",
        f"- Potential outstanding: AUD {money(k['outstanding'])} across {k['unpaid_visits']} visits",
        f"- Cancellation rate: {pct(k['cancel_rate'])}",
        f"- No-show rate: {pct(k['no_show_rate'])}", "",
        "## By clinic", _md_table(by_clinic, {"clinic": "Clinic", **perf}, fmt), "",
        "## By marketing source", _md_table(by_source, {"marketing_source": "Source", **perf}, fmt), "",
        "## Insights", *[f"- {x}" for x in insights], "",
        "## Data quality", *[f"- {key}: {val}" for key, val in quality.items()], "",
        "## Assumptions",
        "- Revenue and collections count completed appointments only.",
        "- Completed = completed, complete, attended, done. Edit clinic_agent/config.py to change this.",
        "- Outstanding is the per-visit shortfall (billed minus collected, never below zero), summed.",
        "- Insights are rule-based. No AI-generated text is included.",
        "- Confirm refunds, partial payments, GST and reschedule handling with the finance lead.",
    ]
    return "\n".join(lines)
