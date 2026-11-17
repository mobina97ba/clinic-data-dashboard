"""Shared settings. Change definitions here, not in the app."""

REQUIRED_COLUMNS = [
    "appointment_id", "clinic", "appointment_date",
    "status", "billed_amount", "collected_amount",
]
OPTIONAL_COLUMNS = ["patient_id", "marketing_source"]

# Common alternative headers, mapped to the expected names.
COLUMN_ALIASES = {
    "id": "appointment_id", "appt_id": "appointment_id",
    "location": "clinic", "branch": "clinic",
    "date": "appointment_date", "appt_date": "appointment_date",
    "appointment_status": "status",
    "billed": "billed_amount", "amount_billed": "billed_amount",
    "collected": "collected_amount", "amount_collected": "collected_amount",
    "paid_amount": "collected_amount",
    "source": "marketing_source",
}

# Status text (lower-case) -> business group. Confirm these with your finance/data lead.
STATUS_GROUPS = {
    "completed": {"completed", "complete", "attended", "done"},
    "cancelled": {"cancelled", "canceled"},
    "no_show": {"no-show", "no show", "noshow"},
}
GROUP_LABELS = {
    "completed": "Completed", "cancelled": "Cancelled",
    "no_show": "No-show", "other": "Other / unrecognised",
}

# Alert thresholds used by the insights.
CANCEL_RATE_ALERT = 0.10
NO_SHOW_RATE_ALERT = 0.05
COLLECTION_RATE_ALERT = 0.90
MIN_GROUP_SIZE = 3  # ignore groups smaller than this when ranking sources/clinics
