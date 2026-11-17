"""Column normalisation, validation and cleaning."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import COLUMN_ALIASES, OPTIONAL_COLUMNS, REQUIRED_COLUMNS, STATUS_GROUPS


class MissingColumnsError(ValueError):
    def __init__(self, missing: list[str], found: list[str]):
        super().__init__("Missing required columns: " + ", ".join(missing))
        self.missing, self.found = missing, found


@dataclass
class CleanResult:
    clean: pd.DataFrame      # usable rows with derived columns
    excluded: pd.DataFrame   # rows left out, with a reason
    quality: dict            # counts shown in the Data quality tab
    rows_uploaded: int


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in out.columns]
    for alias, target in COLUMN_ALIASES.items():
        if alias in out.columns and target not in out.columns:
            out = out.rename(columns={alias: target})
    return out


def _to_number(s: pd.Series) -> pd.Series:
    text = s.astype("string").str.replace(r"[$,\s]", "", regex=True)
    nums = pd.to_numeric(text, errors="coerce")
    return pd.Series(np.asarray(nums, dtype="float64"), index=s.index)


def _canonical_labels(s: pd.Series) -> pd.Series:
    """Strip whitespace and merge spellings that differ only by case."""
    s = s.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    s = s.mask(s.eq(""))
    key = s.str.lower()
    valid = s.notna()
    if not valid.any():
        return s
    common = s[valid].groupby(key[valid]).agg(lambda x: x.value_counts().index[0])
    return key.map(common).astype("string")


def _parse_dates(s: pd.Series) -> pd.Series:
    """ISO dates (2025-03-01) are read as-is; everything else is read day-first (Australian)."""
    text = s.astype("string").str.strip()
    parsed = pd.to_datetime(text, errors="coerce", format="ISO8601")
    rest = pd.to_datetime(text[parsed.isna()], errors="coerce", format="mixed", dayfirst=True)
    return parsed.fillna(rest)


def _status_group(status: pd.Series) -> pd.Series:
    lookup = {v: g for g, values in STATUS_GROUPS.items() for v in values}
    return status.map(lookup).fillna("other").astype(str)


def clean_data(raw: pd.DataFrame) -> CleanResult:
    original = normalise_columns(raw).reset_index(drop=True)
    missing = [c for c in REQUIRED_COLUMNS if c not in original.columns]
    if missing:
        raise MissingColumnsError(missing, list(original.columns))

    df = original.copy()
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    df["appointment_id"] = df["appointment_id"].astype("string").str.strip().replace("", pd.NA)
    df["appointment_date"] = _parse_dates(df["appointment_date"])
    for col in ("billed_amount", "collected_amount"):
        df[col] = _to_number(df[col])
    df["clinic"] = _canonical_labels(df["clinic"])
    df["status"] = df["status"].astype("string").str.strip().str.lower()
    df["status_group"] = _status_group(df["status"])
    df["marketing_source"] = _canonical_labels(df["marketing_source"]).fillna("Unknown")
    df["patient_id"] = df["patient_id"].astype("string").str.strip()

    missing_id = df["appointment_id"].isna()
    duplicate = df["appointment_id"].duplicated(keep="first") & ~missing_id
    invalid_date = df["appointment_date"].isna()
    invalid_amount = df[["billed_amount", "collected_amount"]].isna().any(axis=1)
    negative = (df[["billed_amount", "collected_amount"]] < 0).any(axis=1)
    missing_clinic = df["clinic"].isna()

    # Priority order decides the single reason shown per excluded row.
    checks = [
        ("Missing appointment ID", missing_id), ("Duplicate appointment ID", duplicate),
        ("Invalid date", invalid_date), ("Missing or non-numeric amount", invalid_amount),
        ("Negative amount", negative), ("Missing clinic", missing_clinic),
    ]
    reason = pd.Series("", index=df.index, dtype=object)
    for label, mask in reversed(checks):
        reason = reason.mask(mask, label)
    drop = reason.ne("")

    excluded = original.loc[drop].copy()
    excluded.insert(0, "source_row", excluded.index + 2)  # +2: header row, 1-based
    excluded["reason"] = reason[drop]

    clean = df.loc[~drop].copy()
    clean["month"] = clean["appointment_date"].dt.to_period("M").astype(str)

    quality = {
        "Rows uploaded": len(df),
        "Missing appointment IDs": int(missing_id.sum()),
        "Duplicate appointment IDs": int(duplicate.sum()),
        "Invalid dates": int(invalid_date.sum()),
        "Missing / non-numeric amounts": int(invalid_amount.sum()),
        "Negative amounts": int(negative.sum()),
        "Missing clinic": int(missing_clinic.sum()),
        "Unrecognised statuses": int((df["status_group"] == "other").sum()),
        "Rows excluded": int(drop.sum()),
        "Usable rows": len(clean),
    }
    return CleanResult(clean.reset_index(drop=True), excluded.reset_index(drop=True),
                       quality, len(df))
