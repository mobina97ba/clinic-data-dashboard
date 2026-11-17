"""The SQL layer must agree with the independent pandas implementation."""
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from clinic_agent import by_dimension, clean_data, monthly, summarise  # noqa: E402
from clinic_agent.warehouse import build_warehouse, read_table, run_checks  # noqa: E402

FILES = {"clean": ROOT / "sample_data" / "clinic_appointments.csv",
         "messy": ROOT / "sample_data" / "clinic_appointments_messy.csv"}


class WarehouseTests(unittest.TestCase):
    def setUp(self):
        self.cases = {}
        for name, path in FILES.items():
            raw = pd.read_csv(path)
            self.cases[name] = (build_warehouse(raw), clean_data(raw))

    def test_checks_pass_on_both_samples(self):
        for name, (conn, _) in self.cases.items():
            for r in run_checks(conn):
                self.assertTrue(r["passed"], f"{name}: {r['check']} failed")

    def test_row_counts_match_python_cleaner(self):
        for name, (conn, py) in self.cases.items():
            self.assertEqual(len(read_table(conn, "fct_appointments")), py.quality["Usable rows"], name)
            self.assertEqual(len(read_table(conn, "rejected_appointments")), py.quality["Rows excluded"], name)

    def test_rejection_reasons_match_python_cleaner(self):
        conn, py = self.cases["messy"]
        sql = read_table(conn, "rejected_appointments").sort_values("source_row")
        self.assertEqual(sql["source_row"].tolist(), py.excluded["source_row"].tolist())
        self.assertEqual(sql["reason"].tolist(), py.excluded["reason"].tolist())

    def test_kpis_match_python(self):
        for name, (conn, py) in self.cases.items():
            sql = read_table(conn, "mart_kpis").iloc[0]
            k = summarise(py.clean)
            for key in ("appointments", "completed", "cancelled", "no_show", "billed",
                        "collected", "outstanding", "unpaid_visits"):
                self.assertAlmostEqual(float(sql[key]), float(k[key]), places=6, msg=f"{name}:{key}")
            self.assertAlmostEqual(sql["collection_rate"], k["collection_rate"], places=9)

    def test_clean_sample_headline_numbers(self):
        sql = read_table(self.cases["clean"][0], "mart_kpis").iloc[0]
        self.assertEqual((sql["billed"], sql["collected"], sql["outstanding"]), (6690, 6120, 570))

    def test_group_marts_match_python(self):
        for name, (conn, py) in self.cases.items():
            for table, col, fn in (("mart_by_clinic", "clinic", lambda d: by_dimension(d, "clinic")),
                                   ("mart_by_source", "marketing_source", lambda d: by_dimension(d, "marketing_source")),
                                   ("mart_monthly", "month", monthly)):
                s = read_table(conn, table).set_index(col).sort_index()
                p = fn(py.clean).set_index(col).sort_index()
                self.assertEqual(list(s.index), list(p.index), f"{name}:{table}")
                for m in ("appointments", "billed", "collected", "outstanding"):
                    for a, b in zip(s[m], p[m]):
                        self.assertAlmostEqual(float(a), float(b), places=6, msg=f"{name}:{table}:{m}")

    def test_a_failing_check_is_detected(self):
        conn, _ = self.cases["clean"]
        conn.execute("INSERT INTO fct_appointments (appointment_id, clinic, status_group, billed_amount, collected_amount) "
                     "VALUES ('A1001', 'X', 'completed', -5, 0)")
        failed = {r["check"] for r in run_checks(conn) if not r["passed"]}
        self.assertIn("assert_unique_appointment_id", failed)
        self.assertIn("assert_amounts_not_negative", failed)


if __name__ == "__main__":
    unittest.main()
