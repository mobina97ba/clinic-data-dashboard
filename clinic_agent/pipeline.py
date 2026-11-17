"""Command line entry point.

    python -m clinic_agent.pipeline --input sample_data/clinic_appointments_messy.csv --db warehouse.db
"""
import argparse
import sys

import pandas as pd

from .warehouse import build_warehouse, read_table, run_checks


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Load an appointment export into a SQL warehouse and run checks.")
    p.add_argument("--input", required=True, help="CSV or XLSX appointment export")
    p.add_argument("--db", default=":memory:", help="SQLite file to write (default: in memory)")
    args = p.parse_args(argv)

    raw = pd.read_csv(args.input) if args.input.lower().endswith(".csv") else pd.read_excel(args.input)
    conn = build_warehouse(raw, args.db)

    n_raw = conn.execute("SELECT COUNT(*) FROM raw_appointments").fetchone()[0]
    n_ok = conn.execute("SELECT COUNT(*) FROM fct_appointments").fetchone()[0]
    print(f"Loaded {n_raw} rows -> {n_ok} passed validation, {n_raw - n_ok} rejected")

    rejected = read_table(conn, "rejected_appointments")
    if not rejected.empty:
        print("\nRejected rows:")
        print(rejected.to_string(index=False))

    print("\nData checks:")
    results = run_checks(conn)
    for r in results:
        print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['check']}")

    print("\nKPIs (from SQL):")
    print(read_table(conn, "mart_kpis").T.to_string(header=False))
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
