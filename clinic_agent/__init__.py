"""Clinic Data Intelligence: load, validate and summarise appointment exports."""
from .cleaning import CleanResult, MissingColumnsError, clean_data
from .kpis import by_dimension, filter_data, monthly, repeat_patients, status_counts, summarise
from .insights import build_llm_prompt, generate_insights
from .report import build_report

__all__ = [
    "CleanResult", "MissingColumnsError", "clean_data", "summarise", "by_dimension", "monthly",
    "filter_data", "repeat_patients", "status_counts", "generate_insights",
    "build_llm_prompt", "build_report",
]
