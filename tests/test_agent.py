"""Run with:  python -m unittest discover -s tests -v   (or: pytest)"""
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from clinic_agent import (MissingColumnsError, build_report, by_dimension, clean_data,  # noqa: E402
                          generate_insights, monthly, summarise)

CLEAN = ROOT / "sample_data" / "clinic_appointments.csv"
MESSY = ROOT / "sample_data" / "clinic_appointments_messy.csv"


def frame(rows):
    cols = ["appointment_id", "clinic", "appointment_date", "status", "billed_amount", "collected_amount"]
    return pd.DataFrame(rows, columns=cols)


class CleaningTests(unittest.TestCase):
    def test_clean_sample_has_no_issues(self):
        r = clean_data(pd.read_csv(CLEAN))
        self.assertEqual(r.quality["Rows excluded"], 0)
        self.assertEqual(r.quality["Usable rows"], 20)

    def test_messy_sample_flags_each_problem(self):
        r = clean_data(pd.read_csv(MESSY))
        q = r.quality
        self.assertEqual(q["Rows uploaded"], 22)
        self.assertEqual(q["Duplicate appointment IDs"], 1)
        self.assertEqual(q["Missing appointment IDs"], 1)
        self.assertEqual(q["Invalid dates"], 2)
        self.assertEqual(q["Missing / non-numeric amounts"], 1)
        self.assertEqual(q["Negative amounts"], 1)
        self.assertEqual(q["Missing clinic"], 1)
        self.assertEqual(q["Unrecognised statuses"], 1)
        self.assertEqual(q["Usable rows"], 15)
        self.assertEqual(len(r.excluded), 7)

    def test_negative_amounts_are_excluded_from_kpis(self):
        r = clean_data(frame([["A1", "X", "2025-01-01", "completed", -50, 0],
                              ["A2", "X", "2025-01-02", "completed", 100, 100]]))
        self.assertEqual(summarise(r.clean)["billed"], 100)

    def test_currency_text_and_clinic_case_are_normalised(self):
        r = clean_data(frame([["A1", "Richmond", "2025-01-01", "completed", "$1,200", "900"],
                              ["A2", " richmond ", "2025-01-02", "Completed", 100, 100]]))
        self.assertEqual(r.clean["clinic"].nunique(), 1)
        self.assertEqual(summarise(r.clean)["billed"], 1300)

    def test_dates_iso_and_day_first(self):
        r = clean_data(frame([["A1", "X", "2025-03-01", "completed", 1, 1],
                              ["A2", "X", "03/04/2025", "completed", 1, 1]]))
        self.assertEqual(list(r.clean["month"]), ["2025-03", "2025-04"])

    def test_missing_required_column_raises(self):
        with self.assertRaises(MissingColumnsError):
            clean_data(pd.DataFrame({"clinic": ["X"]}))

    def test_column_aliases(self):
        df = frame([["A1", "X", "2025-01-01", "completed", 1, 1]]).rename(
            columns={"clinic": "Location", "billed_amount": "Amount Billed"})
        self.assertEqual(clean_data(df).quality["Usable rows"], 1)


class KpiTests(unittest.TestCase):
    def setUp(self):
        self.clean = clean_data(pd.read_csv(CLEAN)).clean

    def test_headline_numbers(self):
        k = summarise(self.clean)
        self.assertEqual(k["appointments"], 20)
        self.assertEqual(k["completed"], 14)
        self.assertEqual(k["billed"], 6690)
        self.assertEqual(k["collected"], 6120)
        self.assertEqual(k["outstanding"], 570)
        self.assertEqual(k["unpaid_visits"], 4)
        self.assertAlmostEqual(k["cancel_rate"], 0.15)
        self.assertAlmostEqual(k["no_show_rate"], 0.15)

    def test_outstanding_is_per_visit(self):
        r = clean_data(frame([["A1", "X", "2025-01-01", "completed", 100, 150],
                              ["A2", "X", "2025-01-02", "completed", 200, 100]]))
        self.assertEqual(summarise(r.clean)["outstanding"], 100)  # not 50

    def test_only_completed_visits_count_as_revenue(self):
        r = clean_data(frame([["A1", "X", "2025-01-01", "cancelled", 500, 0],
                              ["A2", "X", "2025-01-02", "no-show", 300, 0]]))
        k = summarise(r.clean)
        self.assertEqual(k["billed"], 0)
        self.assertEqual(k["lost_rate"], 1.0)

    def test_empty_data_does_not_crash(self):
        k = summarise(self.clean.iloc[0:0])
        self.assertEqual(k["appointments"], 0)
        self.assertEqual(k["collection_rate"], 0.0)

    def test_groupings_add_up(self):
        self.assertEqual(by_dimension(self.clean, "clinic")["billed"].sum(), 6690)
        self.assertEqual(monthly(self.clean)["billed"].tolist(), [1760, 1960, 2970])


class OutputTests(unittest.TestCase):
    def test_report_and_insights(self):
        r = clean_data(pd.read_csv(MESSY))
        k = summarise(r.clean)
        bc, bs, bm = by_dimension(r.clean, "clinic"), by_dimension(r.clean, "marketing_source"), monthly(r.clean)
        tips = generate_insights(k, bc, bs, bm, r.quality)
        self.assertTrue(any("excluded" in t for t in tips))
        report = build_report("messy.csv", k, bc, bs, tips, r.quality)
        self.assertIn("# Clinic Data Intelligence Report", report)
        self.assertIn("| Clinic |", report)


if __name__ == "__main__":
    unittest.main()
