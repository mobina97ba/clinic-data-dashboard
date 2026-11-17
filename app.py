"""Clinic Data Intelligence: Streamlit app.  Run with:  streamlit run app.py"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from clinic_agent import (MissingColumnsError, build_report, by_dimension, clean_data, filter_data,
                          generate_insights, monthly, repeat_patients, status_counts, summarise)
from clinic_agent.config import OPTIONAL_COLUMNS, REQUIRED_COLUMNS

BASE = Path(__file__).parent
SAMPLES = {
    "Clean sample": BASE / "sample_data" / "clinic_appointments.csv",
    "Messy sample (shows the data checks)": BASE / "sample_data" / "clinic_appointments_messy.csv",
}

st.set_page_config(page_title="Clinic Data Intelligence", page_icon="🦷", layout="wide")
st.title("🦷 Clinic Data Intelligence")
st.caption("Upload an appointment export and get KPIs, clinic and marketing comparisons, "
           "data-quality checks and a management report.")
st.info("Demo only. Use synthetic or properly de-identified data. Do not upload names, contact "
        "details, dates of birth or health information.")


def read_table(file) -> pd.DataFrame:
    name = getattr(file, "name", str(file)).lower()
    return pd.read_csv(file) if name.endswith(".csv") else pd.read_excel(file)


@st.cache_data
def run_cleaning(raw: pd.DataFrame):
    return clean_data(raw)


# ---------------------------------------------------------------- sidebar: data
with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload appointment data", type=["csv", "xlsx"])
    sample_name = st.radio("…or use a sample", list(SAMPLES), disabled=uploaded is not None)
    with st.expander("Expected columns"):
        st.write("Required: " + ", ".join(REQUIRED_COLUMNS))
        st.write("Optional: " + ", ".join(OPTIONAL_COLUMNS))

try:
    if uploaded is not None:
        raw, source_name = read_table(uploaded), uploaded.name
    else:
        raw, source_name = read_table(SAMPLES[sample_name]), SAMPLES[sample_name].name
    result = run_cleaning(raw)
except MissingColumnsError as exc:
    st.error(str(exc))
    st.write("Columns found:", exc.found)
    st.stop()
except Exception as exc:  # unreadable file
    st.error(f"Could not read the file: {exc}")
    st.stop()

clean = result.clean
if clean.empty:
    st.warning("No usable rows remain after validation. Open the Data quality tab for the reasons.")
    st.dataframe(result.excluded, width="stretch")
    st.stop()

# -------------------------------------------------------------- sidebar: filters
with st.sidebar:
    st.header("Filters")
    clinics = sorted(clean["clinic"].unique())
    sources = sorted(clean["marketing_source"].unique())
    chosen_clinics = st.multiselect("Clinics", clinics, default=clinics)
    chosen_sources = st.multiselect("Marketing sources", sources, default=sources)
    lo, hi = clean["appointment_date"].min().date(), clean["appointment_date"].max().date()
    picked = st.date_input("Appointment dates", value=(lo, hi), min_value=lo, max_value=hi)
    start, end = (picked if isinstance(picked, (tuple, list)) and len(picked) == 2 else (lo, hi))

df = filter_data(clean, chosen_clinics, chosen_sources, start, end)
if df.empty:
    st.warning("No records match the selected filters.")
    st.stop()

k = summarise(df)
by_clinic = by_dimension(df, "clinic")
by_source = by_dimension(df, "marketing_source")
by_month = monthly(df)
tips = generate_insights(k, by_clinic, by_source, by_month, result.quality)
repeat = repeat_patients(df)

st.caption(f"Source: {source_name} · {len(clean):,} usable rows from {result.rows_uploaded:,} uploaded · "
           f"{len(df):,} after filters")

c = st.columns(6)
c[0].metric("Appointments", f"{k['appointments']:,}")
c[1].metric("Completed", f"{k['completed']:,}", f"{k['completion_rate']:.1%} of bookings", delta_color="off")
c[2].metric("Billed revenue", f"${k['billed']:,.0f}")
c[3].metric("Collections", f"${k['collected']:,.0f}", f"{k['collection_rate']:.1%} of billed", delta_color="off")
c[4].metric("Outstanding*", f"${k['outstanding']:,.0f}", f"{k['unpaid_visits']} visits", delta_color="off")
c[5].metric("Repeat patients", f"{repeat['rate']:.0%}" if repeat else "n/a",
            f"{repeat['repeat']} of {repeat['patients']}" if repeat else None, delta_color="off")
st.caption("*Outstanding = per-visit shortfall (billed minus collected, never below zero) on completed visits. "
           "Confirm against finance rules.")

tab_over, tab_seg, tab_dq, tab_rep = st.tabs(["Overview", "Clinics & marketing", "Data quality", "Report"])

with tab_over:
    st.subheader("Automated insights")
    st.caption("Rule-based, calculated from the numbers above. No AI model is involved.")
    for t in tips:
        st.markdown(f"- {t}")
    left, right = st.columns(2)
    with left:
        st.subheader("Revenue by clinic")
        if not by_clinic.empty and by_clinic["billed"].sum() > 0:
            fig = px.bar(by_clinic, x="clinic", y=["billed", "collected"], barmode="group",
                         labels={"value": "Amount (AUD)", "variable": "Measure", "clinic": "Clinic"})
            st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("Appointment status")
        st.plotly_chart(px.pie(status_counts(df), names="status", values="appointments", hole=0.45),
                        width="stretch")
    st.subheader("Monthly trend")
    if not by_month.empty:
        st.plotly_chart(px.line(by_month, x="month", y=["billed", "collected"], markers=True,
                                labels={"value": "Amount (AUD)", "variable": "Measure", "month": "Month"}),
                        width="stretch")

with tab_seg:
    cols = {"appointments": "Appointments", "completed": "Completed", "lost_rate": "Cancel + no-show rate",
            "billed": "Billed", "collected": "Collected", "collection_rate": "Collection rate"}
    fmt = {"Cancel + no-show rate": "{:.1%}", "Collection rate": "{:.1%}", "Billed": "${:,.0f}",
           "Collected": "${:,.0f}"}
    st.subheader("By clinic")
    st.dataframe(by_clinic[["clinic", *cols]].rename(columns={"clinic": "Clinic", **cols}).style.format(fmt),
                 width="stretch", hide_index=True)
    st.plotly_chart(px.bar(by_clinic, x="clinic", y="lost_rate",
                           labels={"lost_rate": "Cancel + no-show rate", "clinic": "Clinic"}).update_yaxes(tickformat=".0%"),
                    width="stretch")
    st.subheader("By marketing source")
    st.dataframe(by_source[["marketing_source", *cols]].rename(columns={"marketing_source": "Source", **cols})
                 .style.format(fmt), width="stretch", hide_index=True)
    st.plotly_chart(px.bar(by_source, x="marketing_source", y="collected",
                           labels={"collected": "Collected (AUD)", "marketing_source": "Source"}),
                    width="stretch")

with tab_dq:
    q = result.quality
    st.subheader("Checks")
    st.dataframe(pd.DataFrame({"Check": list(q), "Count": list(q.values())}), width="stretch", hide_index=True)
    st.subheader("Rows left out of the analysis")
    if result.excluded.empty:
        st.success("No rows were excluded.")
    else:
        st.caption("`source_row` is the row number in your file, counting the header as row 1.")
        st.dataframe(result.excluded, width="stretch", hide_index=True)
        st.download_button("Download excluded rows (CSV)", result.excluded.to_csv(index=False).encode("utf-8"),
                           "excluded_rows.csv", "text/csv")

with tab_rep:
    report = build_report(source_name, k, by_clinic, by_source, tips, result.quality)
    st.markdown(report)
    d1, d2 = st.columns(2)
    d1.download_button("Download management report (Markdown)", report.encode("utf-8"),
                       "clinic_management_report.md", "text/markdown")
    d2.download_button("Download cleaned data (CSV)",
                       df.drop(columns=["month"]).to_csv(index=False).encode("utf-8"),
                       "clinic_cleaned_data.csv", "text/csv")
    with st.expander("Preview cleaned data"):
        st.dataframe(df.head(100), width="stretch")

st.markdown("---")
st.caption("Portfolio project · Python · pandas · Streamlit · Plotly")
