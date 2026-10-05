"""The replay entry point separates version records from scientific results."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import reproduce_all as replay
from result_validation import ResultMismatch


class ReplayPortabilityTests(unittest.TestCase):
    def setUp(self):
        integer_columns = sorted(replay.ALERT_INTEGER_COLUMNS)
        header = ["date", *integer_columns, "G"]
        values = ["2021-01-05", *("12" if key == "N" else "0" for key in integer_columns), "0.1"]
        self.carrier = (",".join(header) + "\n" + ",".join(values) + "\n").encode("ascii")
        self.reference = {
            "provenance": {"python": "3.12.14", "numpy": "2.3.5",
                "input_hashes": {"prices.csv": "input-identity"},
                "analysis_sha256": "analysis-identity"},
            "sample": {"pairs": 1296, "counties": 12},
            "month_r2": 0.04969532,
            "calendar_comparisons": {"source": {
                "path": "results/alerts/alerts_daily.csv",
                "sha256": hashlib.sha256(self.carrier).hexdigest()}}}

    def compare(self, reference, actual, relative="results/benchmark_checks/seasonality_summary.json"):
        function = getattr(replay, "compare_result_json", None)
        self.assertTrue(callable(function), "The complete replay needs its runtime-aware result dispatcher")
        return function(relative, reference, actual,
            expected_source_bytes=self.carrier, actual_source_bytes=self.carrier)

    def test_version_only_difference_passes_at_actual_replay_entry(self):
        actual = copy.deepcopy(self.reference)
        actual["provenance"].update(python="3.12.13", numpy="2.4.1")
        report = self.compare(self.reference, actual)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual({tuple(item["path"]) for item in report["informational_fields"]},
                         {("provenance", "python"), ("provenance", "numpy")})
        self.assertTrue(report["derived_source"]["recorded_digests_verified"])

    def test_optional_version_leaf_is_recorded_when_absent(self):
        actual = copy.deepcopy(self.reference)
        del actual["provenance"]["python"]
        report = self.compare(self.reference, actual)
        python = next(item for item in report["informational_fields"]
                      if item["path"] == ["provenance", "python"])
        self.assertTrue(python["expected_present"])
        self.assertFalse(python["actual_present"])

    def test_scientific_counts_and_numerical_changes_still_fail(self):
        for field, value in [("pairs", 1297), ("counties", 11)]:
            actual = copy.deepcopy(self.reference)
            actual["sample"][field] = value
            with self.subTest(field=field), self.assertRaises(ResultMismatch):
                self.compare(self.reference, actual)
        actual = copy.deepcopy(self.reference)
        actual["month_r2"] += 1e-5
        with self.assertRaises(ResultMismatch):
            self.compare(self.reference, actual)

    def test_input_and_method_identity_remain_strict(self):
        for field in ["input_hashes", "analysis_sha256"]:
            actual = copy.deepcopy(self.reference)
            actual["provenance"][field] = ({"prices.csv": "different"}
                if field == "input_hashes" else "different")
            with self.subTest(field=field), self.assertRaises(ResultMismatch):
                self.compare(self.reference, actual)

    def test_other_result_artifacts_do_not_inherit_exclusions(self):
        actual = copy.deepcopy(self.reference)
        actual["provenance"]["python"] = "3.12.13"
        with self.assertRaises(ResultMismatch):
            self.compare(self.reference, actual, "results/primary_15_L6.json")

    def test_derived_source_digest_cannot_be_bypassed_by_versions(self):
        actual = copy.deepcopy(self.reference)
        actual["provenance"]["python"] = "3.12.13"
        actual["calendar_comparisons"]["source"]["sha256"] = "0" * 64
        with self.assertRaises(ResultMismatch):
            self.compare(self.reference, actual)


if __name__ == "__main__":
    unittest.main()
