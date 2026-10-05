"""Scientific validation tests use fixed small summaries, not a scientific replay."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
try:
    import result_validation as validation
except ModuleNotFoundError:
    validation = None

# Public regression fixture copied from the accepted alerts summary. This is
# intentionally small so the same tests run in a source-only repository checkout.
ALERT_CASES = [
    {"benchmark": "B0", "cohort": "Full12", "rule": "aggregate_three_dates", "N": 12,
     "complete_monitoring_dates": 204, "trigger_dates": 19, "episodes": 4,
     "first": "2021-10-25", "last": "2025-01-25"},
    {"benchmark": "B2", "cohort": "Full12", "rule": "aggregate_three_dates", "N": 12,
     "complete_monitoring_dates": 204, "trigger_dates": 126, "episodes": 4,
     "first": "2021-07-05", "last": "2025-05-05"},
    {"benchmark": "B2", "cohort": "S6", "rule": "aggregate_three_dates", "N": 6,
     "complete_monitoring_dates": 204, "trigger_dates": 131, "episodes": 3,
     "first": "2021-07-05", "last": "2025-04-25"},
    {"benchmark": "B3", "cohort": "Full12", "rule": "aggregate_three_dates", "N": 12,
     "complete_monitoring_dates": 204, "trigger_dates": 0, "episodes": 0,
     "first": None, "last": None},
    {"benchmark": "B0", "cohort": "Full12", "rule": "H_ge_half", "N": 12,
     "complete_monitoring_dates": 204, "trigger_dates": 31, "episodes": 6,
     "first": "2021-10-05", "last": "2025-01-25"},
    {"benchmark": "B2", "cohort": "S6", "rule": "H_ge_half", "N": 6,
     "complete_monitoring_dates": 204, "trigger_dates": 145, "episodes": 7,
     "first": "2021-06-15", "last": "2026-09-25"},
]


class ScientificResultTests(unittest.TestCase):
    def runtime_case(self):
        return {"provenance": {"python": "3.12.14", "numpy": "2.3.5",
                    "input_hashes": {"prices.csv": "a" * 64},
                    "analysis_sha256": "b" * 64},
                "runtime": {"node": "24.16.0", "platform": "macOS"},
                "science": {"python": "fixed method", "count": 19,
                            "classification": "attained", "mean": 0.5},
                "configuration": {"draws": 9999}}

    def test_runtime_versions_are_informational_only_at_declared_paths(self):
        expected = self.runtime_case()
        actual = copy.deepcopy(expected)
        actual["provenance"].update(python="3.12.15", numpy="2.4.0")
        actual["runtime"].update(node="24.19.0", platform="Linux")
        report = validation.compare_values(expected, actual, informational_paths=(
            ("provenance", "python"), ("provenance", "numpy"),
            ("runtime", "node"), ("runtime", "platform")))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["integer_compared"], 2)
        self.assertEqual(report["informational_fields"], [
            {"path": ["provenance", "python"], "expected_present": True,
             "actual_present": True, "expected": "3.12.14", "actual": "3.12.15"},
            {"path": ["provenance", "numpy"], "expected_present": True,
             "actual_present": True, "expected": "2.3.5", "actual": "2.4.0"},
            {"path": ["runtime", "node"], "expected_present": True,
             "actual_present": True, "expected": "24.16.0", "actual": "24.19.0"},
            {"path": ["runtime", "platform"], "expected_present": True,
             "actual_present": True, "expected": "macOS", "actual": "Linux"}])

    def test_runtime_default_comparison_stays_strict(self):
        expected = self.runtime_case()
        actual = copy.deepcopy(expected)
        actual["provenance"]["python"] = "3.12.15"
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values(expected, actual)

    def test_informational_path_does_not_skip_same_key_in_science(self):
        expected = self.runtime_case()
        actual = copy.deepcopy(expected)
        actual["science"]["python"] = "changed method"
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values(expected, actual,
                informational_paths=(("provenance", "python"),))

    def test_optional_informational_leaf_presence_is_recorded_without_mutation(self):
        before = self.runtime_case()
        after = copy.deepcopy(before)
        del after["provenance"]["python"]
        snapshots = copy.deepcopy((before, after))
        report = validation.compare_values(before, after,
            informational_paths=(("provenance", "python"),))
        self.assertEqual(report["informational_fields"], [
            {"path": ["provenance", "python"], "expected_present": True,
             "actual_present": False, "expected": "3.12.14", "actual": None}])
        reverse = validation.compare_values(after, before,
            informational_paths=(("provenance", "python"),))
        self.assertEqual(reverse["informational_fields"][0]["expected_present"], False)
        self.assertEqual(reverse["informational_fields"][0]["actual"], "3.12.14")
        self.assertEqual((before, after), snapshots)

    def test_missing_or_changed_metadata_parent_remains_a_structural_failure(self):
        before = self.runtime_case()
        for replacement in [None, [], "3.12.15"]:
            after = copy.deepcopy(before)
            after["provenance"] = replacement
            with self.subTest(replacement=replacement), self.assertRaises(validation.ResultMismatch):
                validation.compare_values(before, after,
                    informational_paths=(("provenance", "python"),))
        after = copy.deepcopy(before)
        del after["provenance"]
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values(before, after,
                informational_paths=(("provenance", "python"),))

    def test_informational_exclusions_reject_empty_malformed_and_wildcard_paths(self):
        for paths in ["python", (( ),), ("python",), (("provenance", ""),),
                      (("provenance", None),), (("provenance", True),),
                      (("provenance", -1),), (("provenance", "*"),),
                      (("provenance", "python"), ("provenance", "python"))]:
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                validation.compare_values(self.runtime_case(), self.runtime_case(),
                    informational_paths=paths)

    def test_informational_paths_cannot_exclude_objects_or_numeric_science(self):
        before = self.runtime_case()
        for path in [("provenance",), ("science", "count"),
                     ("science", "mean"), ("configuration",)]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                validation.compare_values(before, copy.deepcopy(before),
                    informational_paths=(path,))
        with self.assertRaises(ValueError):
            validation.compare_values({"versions": ["3.12.14"]},
                {"versions": ["3.12.15"]}, informational_paths=(("versions",),))

    def test_tuple_paths_support_list_indices_without_relaxing_list_shape(self):
        before = {"runs": [{"python": "3.12.14", "count": 19},
                           {"python": "fixed scientific label", "count": 20}]}
        after = copy.deepcopy(before)
        after["runs"][0]["python"] = "3.12.15"
        paths = (("runs", 0, "python"),)
        report = validation.compare_values(before, after, informational_paths=paths)
        self.assertEqual(report["informational_fields"][0]["path"], ["runs", 0, "python"])
        after["runs"][1]["python"] = "changed scientific label"
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values(before, after, informational_paths=paths)
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values(before, {"runs": before["runs"][:1]},
                informational_paths=paths)

    def test_scientific_and_hash_mutations_fail_when_runtime_paths_are_opted_in(self):
        before = self.runtime_case()
        mutations = [("science", "count", 20), ("science", "classification", "below"),
                     ("science", "mean", 0.51), ("configuration", "draws", 10000),
                     ("provenance", "analysis_sha256", "c" * 64)]
        for parent, key, value in mutations:
            after = copy.deepcopy(before)
            after[parent][key] = value
            with self.subTest(parent=parent, key=key), self.assertRaises(validation.ResultMismatch):
                validation.compare_values(before, after,
                    informational_paths=(("provenance", "python"),))
        after = copy.deepcopy(before)
        after["provenance"]["input_hashes"]["prices.csv"] = "c" * 64
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values(before, after,
                informational_paths=(("provenance", "python"),))

    def test_unavailable_informational_version_is_a_reported_null_leaf(self):
        report = validation.compare_values({"runtime": {"python": None}},
            {"runtime": {"python": "3.12.15"}},
            informational_paths=(("runtime", "python"),))
        self.assertEqual(report["informational_fields"][0]["expected"], None)
        self.assertTrue(report["informational_fields"][0]["expected_present"])

    def test_derived_source_verification_combines_with_informational_receipts(self):
        before = b"date,count,G\n2020-01-01,1,0.13383871054301133\n"
        after = b"date,count,G\n2020-01-01,1,0.13383871054301136\n"
        expected, actual = self.derived_source_case(before), self.derived_source_case(after)
        expected["provenance"] = {"python": "3.12.14"}
        actual["provenance"] = {"python": "3.12.15"}
        snapshots = copy.deepcopy((expected, actual))
        report = validation.compare_values_with_derived_source(expected, actual,
            source_keys=("diagnostic", "source"), expected_source_bytes=before,
            actual_source_bytes=after, integer_columns={"count"}, float_columns={"G"},
            informational_paths=(("provenance", "python"),))
        self.assertTrue(report["derived_source"]["recorded_digests_verified"])
        self.assertEqual(report["informational_fields"][0]["actual"], "3.12.15")
        self.assertEqual((expected, actual), snapshots)

    def test_informational_exclusion_cannot_bypass_derived_digest_verification(self):
        raw = b"date,count,G\n2020-01-01,1,0.1\n"
        expected, actual = self.derived_source_case(raw), self.derived_source_case(raw)
        actual["diagnostic"]["source"]["sha256"] = "0" * 64
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values_with_derived_source(expected, actual,
                source_keys=("diagnostic", "source"), expected_source_bytes=raw,
                actual_source_bytes=raw, integer_columns={"count"}, float_columns={"G"},
                informational_paths=(("diagnostic", "source", "sha256"),))

    def test_runtime_metadata_does_not_relax_derived_scientific_or_source_path_checks(self):
        before = b"date,count,G\n2020-01-01,1,0.1\n"
        for after in [b"date,count,G\n2020-01-01,2,0.1\n",
                      b"date,count,G\n2020-01-01,1,0.2\n"]:
            expected, actual = self.derived_source_case(before), self.derived_source_case(after)
            expected["provenance"] = {"python": "3.12.14"}
            actual["provenance"] = {"python": "3.12.15"}
            with self.subTest(after=after), self.assertRaises(validation.ResultMismatch):
                validation.compare_values_with_derived_source(expected, actual,
                    source_keys=("diagnostic", "source"), expected_source_bytes=before,
                    actual_source_bytes=after, integer_columns={"count"}, float_columns={"G"},
                    informational_paths=(("provenance", "python"),))
        expected, actual = self.derived_source_case(before), self.derived_source_case(before)
        expected["provenance"] = {"python": "3.12.14"}
        actual["provenance"] = {"python": "3.12.15"}
        actual["diagnostic"]["source"]["path"] = "other.csv"
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values_with_derived_source(expected, actual,
                source_keys=("diagnostic", "source"), expected_source_bytes=before,
                actual_source_bytes=before, integer_columns={"count"}, float_columns={"G"},
                informational_paths=(("provenance", "python"),))

    def derived_source_case(self, raw):
        return {"diagnostic": {"source": {"path": "daily.csv",
            "sha256": hashlib.sha256(raw).hexdigest()}, "count": 1}}

    def test_derived_source_identity_and_scientific_roundoff_are_separate(self):
        before = b"date,count,G\n2020-01-01,1,0.13383871054301133\n"
        after = b"date,count,G\n2020-01-01,1,0.13383871054301136\n"
        report = validation.compare_values_with_derived_source(
            self.derived_source_case(before), self.derived_source_case(after),
            source_keys=("diagnostic", "source"), expected_source_bytes=before,
            actual_source_bytes=after, integer_columns={"count"}, float_columns={"G"})
        self.assertEqual(report["status"], "PASS")
        self.assertFalse(report["derived_source"]["byte_identity"])
        self.assertTrue(report["derived_source"]["recorded_digests_verified"])

    def test_derived_source_digest_forgery_is_rejected(self):
        raw = b"date,count,G\n2020-01-01,1,0.1\n"
        correct = self.derived_source_case(raw)
        forged = copy.deepcopy(correct)
        forged["diagnostic"]["source"]["sha256"] = "0" * 64
        for before, after in [(forged, correct), (correct, forged)]:
            with self.assertRaises(validation.ResultMismatch):
                validation.compare_values_with_derived_source(before, after,
                    source_keys=("diagnostic", "source"), expected_source_bytes=raw,
                    actual_source_bytes=raw, integer_columns={"count"}, float_columns={"G"})

    def test_derived_source_scientific_change_is_rejected_despite_valid_hashes(self):
        before = b"date,count,G\n2020-01-01,1,0.1\n"
        for after in [b"date,count,G\n2020-01-01,2,0.1\n",
                      b"date,count,G\n2020-01-01,1,0.2\n"]:
            with self.assertRaises(validation.ResultMismatch):
                validation.compare_values_with_derived_source(
                    self.derived_source_case(before), self.derived_source_case(after),
                    source_keys=("diagnostic", "source"), expected_source_bytes=before,
                    actual_source_bytes=after, integer_columns={"count"}, float_columns={"G"})

    def setUp(self):
        self.assertIsNotNone(validation, "Scientific validation entry is required")

    def test_float_roundoff_passes_and_reports_actual_maximum(self):
        expected = {"mean": 0.13383871054301133, "interval": [0.0019954139340366884, 0.0511864879955332]}
        actual = copy.deepcopy(expected)
        actual["mean"] = math.nextafter(expected["mean"], math.inf)
        actual["interval"][1] = math.nextafter(expected["interval"][1], -math.inf)
        report = validation.compare_values(expected, actual)
        self.assertGreater(report["floating_max_abs_difference"], 0)
        self.assertEqual(report["floating_max_abs_difference"],
                         max(abs(expected["mean"] - actual["mean"]),
                             abs(expected["interval"][1] - actual["interval"][1])))
        self.assertEqual(report["floating_compared"], 3)

    def test_material_float_difference_fails(self):
        with self.assertRaisesRegex(validation.ResultMismatch, "floating"):
            validation.compare_values({"mean": 0.1338}, {"mean": 0.13380001})

    def test_relative_tolerance_does_not_replace_absolute_bound(self):
        report = validation.compare_values(1e6, 1e6 + 5e-7)
        self.assertGreater(report["floating_max_abs_difference"], 1e-12)
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values(1e6, 1e6 + 1e-5)

    def test_integer_counts_remain_strict(self):
        with self.assertRaisesRegex(validation.ResultMismatch, "integer"):
            validation.compare_values({"trigger_dates": 19}, {"trigger_dates": 20})
        with self.assertRaisesRegex(validation.ResultMismatch, "integer"):
            validation.compare_values({"trigger_dates": 19}, {"trigger_dates": 19.0})

    def test_classes_booleans_and_null_remain_strict(self):
        for expected, actual in [("PASS", "FAIL"), (True, 1), (None, 0)]:
            with self.subTest(expected=expected), self.assertRaises(validation.ResultMismatch):
                validation.compare_values(expected, actual)

    def test_nonfinite_values_and_structure_changes_fail(self):
        for actual in [float("nan"), float("inf")]:
            with self.subTest(actual=actual), self.assertRaises(validation.ResultMismatch):
                validation.compare_values(1.0, actual)
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values({"counts": [1, 2]}, {"counts": [1]})
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values({"counts": 2}, {"other": 2})

    def test_near_zero_tolerance_is_absolute_and_bounded(self):
        self.assertEqual(validation.compare_values(0.0, 5e-13)["floating_compared"], 1)
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_values(0.0, 2e-12)

    def test_csv_integers_strict_and_float_text_roundoff_allowed(self):
        expected = b"rep,count,mean,class\n1,19,0.13383871054301133,PASS\n"
        actual = b"rep,count,mean,class\n1,19,0.13383871054301136,PASS\n"
        report = validation.compare_csv_bytes(expected, actual, integer_columns={"rep", "count"})
        self.assertEqual(report["integer_compared"], 2)
        self.assertGreater(report["floating_max_abs_difference"], 0)
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_csv_bytes(expected, actual.replace(b",19,", b",20,"), integer_columns={"rep", "count"})

    def test_csv_numeric_class_labels_do_not_coerce(self):
        expected = b"rep,class,mean\n1,01,0.1\n"
        actual = b"rep,class,mean\n1,1,0.1\n"
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_csv_bytes(expected, actual, integer_columns={"rep"})

    def test_binary_coefficient_roundoff_allowed_and_indices_exact(self):
        import struct
        expected = struct.pack("<2d", 0.13, -0.04)
        actual = struct.pack("<2d", math.nextafter(0.13, math.inf), -0.04)
        report = validation.compare_float64_bytes(expected, actual)
        self.assertGreater(report["floating_max_abs_difference"], 0)
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_float64_bytes(expected, struct.pack("<2d", 0.13001, -0.04))
        with self.assertRaises(validation.ResultMismatch):
            validation.compare_exact_bytes(b"\x00\x01", b"\x00\x02")

    def test_alert_summary_fixture_contains_actual_critical_regressions(self):
        fixture = json.loads((ROOT / "tests/fixtures/alerts_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(len(fixture), 45)
        report = validation.validate_alert_summary(fixture, ALERT_CASES)
        self.assertEqual(report["cases_checked"], 6)
        self.assertEqual(report["status"], "PASS")
        bad = copy.deepcopy(fixture)
        next(row for row in bad if row["benchmark"] == "B2" and row["cohort"] == "S6"
             and row["rule"] == "aggregate_three_dates")["trigger_dates"] = 130
        with self.assertRaises(validation.ResultMismatch):
            validation.validate_alert_summary(bad, ALERT_CASES)

    def test_packaged_alert_summary_matches_fixture_when_data_is_present(self):
        path = ROOT / "results/alerts/alerts_summary.json"
        if not path.is_file():
            self.skipTest("Complete-release alerts summary is not present in source-only checkout")
        summary = json.loads(path.read_text(encoding="utf-8"))
        report = validation.validate_alert_summary(summary, ALERT_CASES)
        self.assertEqual(report["cases_checked"], 6)
        self.assertEqual(len(summary), 45)


if __name__ == "__main__":
    unittest.main()
