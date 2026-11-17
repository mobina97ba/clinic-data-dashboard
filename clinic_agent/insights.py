"""Rule-based business insights (no AI involved) plus an optional LLM prompt builder."""
from __future__ import annotations

import pandas as pd

from .config import (CANCEL_RATE_ALERT, COLLECTION_RATE_ALERT, MIN_GROUP_SIZE, NO_SHOW_RATE_ALERT)


def money(x: float) -> str:
    return f"${x:,.0f}"


def pct(x: float) -> str:
    return f"{x:.1%}"


def _eligible(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["appointments"] >= MIN_GROUP_SIZE] if not df.empty else df


def generate_insights(k: dict, by_clinic: pd.DataFrame, by_source: pd.DataFrame,
                      by_month: pd.DataFrame, quality: dict) -> list[str]:
    if k["appointments"] == 0:
        return ["No appointments match the current filters."]
    out = []

    level = "above" if k["cancel_rate"] >= CANCEL_RATE_ALERT else "within"
    out.append(f"Cancellation rate is {pct(k['cancel_rate'])}, {level} the {pct(CANCEL_RATE_ALERT)} alert level."
               + (" Review reminder and rebooking workflows." if level == "above" else ""))
    level = "above" if k["no_show_rate"] >= NO_SHOW_RATE_ALERT else "within"
    out.append(f"No-show rate is {pct(k['no_show_rate'])}, {level} the {pct(NO_SHOW_RATE_ALERT)} alert level."
               + (" Test reminder timing and confirmation steps." if level == "above" else ""))

    clinics = _eligible(by_clinic)
    if len(clinics) > 1:
        top = clinics.iloc[0]
        out.append(f"{top['clinic']} has the highest billed revenue ({money(top['billed'])}).")
        worst = clinics.sort_values("lost_rate", ascending=False).iloc[0]
        out.append(f"{worst['clinic']} loses the most appointments to cancellations and no-shows "
                   f"({pct(worst['lost_rate'])} of its bookings).")
        paying = clinics[clinics["billed"] > 0]
        if not paying.empty:
            low = paying.sort_values("collection_rate").iloc[0]
            if low["collection_rate"] < COLLECTION_RATE_ALERT:
                out.append(f"{low['clinic']} has the lowest collection rate ({pct(low['collection_rate'])}); "
                           "check payment follow-up there.")

    known = by_source[by_source["marketing_source"] != "Unknown"] if not by_source.empty else by_source
    sources = _eligible(known)
    if len(sources) > 1:
        best = sources.sort_values("collected", ascending=False).iloc[0]
        out.append(f"{best['marketing_source']} brings in the most collected revenue ({money(best['collected'])}).")
        weak = sources.sort_values("lost_rate", ascending=False).iloc[0]
        out.append(f"Bookings from {weak['marketing_source']} are lost most often ({pct(weak['lost_rate'])}).")

    if len(by_month) >= 2:
        prev, last = by_month.iloc[-2], by_month.iloc[-1]
        if prev["billed"] > 0:
            change = last["billed"] / prev["billed"] - 1
            out.append(f"Billed revenue in {last['month']} is {change:+.1%} versus {prev['month']}. "
                       "Check the latest month is complete before drawing conclusions.")

    if k["outstanding"] > 0:
        out.append(f"{money(k['outstanding'])} is potentially outstanding across {k['unpaid_visits']} completed "
                   "visits. Reconcile with the finance system before acting.")
    if quality.get("Rows excluded"):
        out.append(f"{quality['Rows excluded']} of {quality['Rows uploaded']} uploaded rows were excluded for "
                   "data-quality reasons. Review them before sharing this report.")
    return out


def build_llm_prompt(k: dict, by_clinic: pd.DataFrame, by_source: pd.DataFrame) -> str:
    """Prompt built from aggregated numbers only. Never pass row-level patient data to an LLM."""
    def table(df, col):
        cols = [col, "appointments", "billed", "collected", "lost_rate"]
        return df[cols].round(3).to_string(index=False) if not df.empty else "n/a"
    return (
        "You are a clinic operations analyst. Using ONLY the figures below, write five plain-English "
        "observations for a practice manager. Do not invent numbers.\n\n"
        f"Overall: {k}\n\nBy clinic:\n{table(by_clinic, 'clinic')}\n\n"
        f"By marketing source:\n{table(by_source, 'marketing_source')}\n"
    )
