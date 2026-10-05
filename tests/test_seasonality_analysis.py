"""Hand-derived scientific checks for descriptive month-factor decomposition."""
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
try:
    import seasonality_analysis as seasonality
except ModuleNotFoundError:
    seasonality = None


class SeasonalityAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(seasonality, "Month-factor analysis is not implemented")

    def factorial_panel(self):
        # Sixteen balanced observations; four orthogonal components have
        # variances 4 (county), 9 (year), 1 (month), and 4 (within-cell error).
        rows = []
        for county, county_effect in [("A", -2), ("B", 2)]:
            for year, year_effect in [(2018, -3), (2019, 3)]:
                for month, month_effect in [(1, -1), (2, 1)]:
                    for day, error in [(5, -2), (15, 2)]:
                        rows.append({"county": county,
                            "date": f"{year}-{month:02d}-{day:02d}",
                            "year": year, "month": month,
                            "y": 10 + county_effect + year_effect + month_effect + error})
        return rows

    def test_partial_r_squared_uses_reduced_residual_variance(self):
        # Catches use of TSS in partial R² or mixing raw and incremental R².
        result = seasonality.analyze_panel(self.factorial_panel(), "y", "panel_equal")
        self.assertAlmostEqual(result["tss"], 288)
        self.assertAlmostEqual(result["models"]["month"]["sse"], 272)
        self.assertAlmostEqual(result["models"]["county_year"]["sse"], 80)
        self.assertAlmostEqual(result["models"]["county_year_month"]["sse"], 64)
        self.assertAlmostEqual(result["raw_month_r2"], 1 / 18)
        self.assertAlmostEqual(result["incremental_month_r2"], 1 / 18)
        self.assertAlmostEqual(result["partial_month_r2"], 1 / 5)
        self.assertEqual([result["models"][name]["rank"] for name in
            ["month", "county_year", "county_year_month"]], [2, 3, 4])
        self.assertEqual(result["month_rank_increment"], 1)

    def test_aliased_month_year_has_no_incremental_explanation(self):
        # Each year contains only its corresponding month. Raw month R² is
        # 9/17, entirely confounded with year; added month rank and SSE gain=0.
        rows = []
        for county, county_effect in [("A", -2), ("B", 2)]:
            for year, month, year_effect in [(2018, 1, -3), (2019, 2, 3)]:
                for day, error in [(5, -2), (15, 2)]:
                    rows.append({"county": county, "year": year, "month": month,
                        "date": f"{year}-{month:02d}-{day:02d}",
                        "y": 10 + county_effect + year_effect + error})
        result = seasonality.analyze_panel(rows, "y", "panel_equal")
        self.assertAlmostEqual(result["raw_month_r2"], 9 / 17)
        self.assertAlmostEqual(result["incremental_month_r2"], 0)
        self.assertAlmostEqual(result["partial_month_r2"], 0)
        self.assertEqual(result["month_rank_increment"], 0)
        self.assertEqual(result["models"]["county_year_month"]["rank"], 3)
        self.assertEqual(result["models"]["county_year_month"]["design_columns"], 4)

    def test_equal_date_weights_do_not_overweight_more_populated_dates(self):
        # Dates have 2,1,2 observations and means 0,2,4. Ordinary panel weights
        # give raw month R²=5/6; weights 1/n_t give TSS=8,SSE=2,R²=3/4.
        rows = [
            {"county": "A", "date": "2018-01-05", "year": 2018, "month": 1, "y": 0},
            {"county": "B", "date": "2018-01-05", "year": 2018, "month": 1, "y": 0},
            {"county": "A", "date": "2018-01-15", "year": 2018, "month": 1, "y": 2},
            {"county": "A", "date": "2018-02-05", "year": 2018, "month": 2, "y": 4},
            {"county": "B", "date": "2018-02-05", "year": 2018, "month": 2, "y": 4},
        ]
        ordinary = seasonality.analyze_panel(rows, "y", "panel_equal")
        weighted = seasonality.analyze_panel(rows, "y", "date_equal")
        self.assertAlmostEqual(ordinary["raw_month_r2"], 5 / 6)
        self.assertAlmostEqual(weighted["raw_month_r2"], 3 / 4)
        self.assertAlmostEqual(weighted["tss"], 8)
        self.assertAlmostEqual(weighted["models"]["month"]["sse"], 2)
        self.assertAlmostEqual(weighted["weight_sum"], 3)

    def test_constant_outcome_explanation_is_undefined(self):
        # A constant price ratio has no total variance; it cannot earn R²=1.
        rows = self.factorial_panel()
        for row in rows:
            row["y"] = 7.0
        result = seasonality.analyze_panel(rows, "y", "panel_equal")
        for field in ["raw_month_r2", "incremental_month_r2", "partial_month_r2"]:
            self.assertIsNone(result[field])
        self.assertEqual(result["variance_status"], "ZERO_TOTAL_VARIANCE")

    def test_exact_county_fit_leaves_partial_r_squared_undefined(self):
        # County effects fit all variation; floating-point SSE must not yield
        # a spurious ratio for partial R² when the reduced residual is zero.
        rows = self.factorial_panel()
        for row in rows:
            row["y"] = 1.0 if row["county"] == "A" else 2.0
        result = seasonality.analyze_panel(rows, "y", "panel_equal")
        self.assertAlmostEqual(result["incremental_month_r2"], 0)
        self.assertIsNone(result["partial_month_r2"])
        self.assertEqual(result["variance_status"], "ZERO_REDUCED_RESIDUAL_VARIANCE")

    def quote(self, county, date, product, value, source="old"):
        return {"region_id": county, "region_name": county, "date": date,
            "product_id": product,
            "specification": "混等收购价" if product == "maize_purchase_mixed" else "国产",
            "unit": "元/500克", "value": value, "source_id": source,
            "status": "observed" if value not in ["0", "-"] else "missing_value",
            "analysis_eligible": "True" if value not in ["0", "-"] else "False"}

    def write_quotes(self, path, rows):
        with path.open("w", encoding="utf-8-sig", newline="") as destination:
            writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_pairing_is_strictly_in_range_positive_same_source_and_unimputed(self):
        # Catches inclusion of out-of-window data, zero quotes, source
        # stitching, missing partners, or arithmetic-level/log confusion.
        rows = [
            self.quote("A", "2017-12-25", "maize_purchase_mixed", "9"),
            self.quote("A", "2017-12-25", "urea_domestic", "1"),
            self.quote("A", "2018-01-05", "maize_purchase_mixed", "2"),
            self.quote("A", "2018-01-05", "urea_domestic", "4"),
            self.quote("A", "2019-01-05", "maize_purchase_mixed", "0"),
            self.quote("A", "2019-01-05", "urea_domestic", "1"),
            self.quote("A", "2019-02-05", "maize_purchase_mixed", "1"),
            self.quote("A", "2019-02-05", "urea_domestic", "1", "new"),
            self.quote("A", "2019-03-05", "maize_purchase_mixed", "1"),
            self.quote("A", "2020-12-25", "maize_purchase_mixed", "3"),
            self.quote("A", "2020-12-25", "urea_domestic", "2"),
            self.quote("A", "2021-01-05", "maize_purchase_mixed", "9"),
            self.quote("A", "2021-01-05", "urea_domestic", "1"),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "quotes.csv"
            self.write_quotes(path, rows)
            paired, audit = seasonality.load_quote_pairs(path, ["A"])
        self.assertEqual([row["date"] for row in paired], ["2018-01-05", "2020-12-25"])
        self.assertEqual([row["level_ratio"] for row in paired], [0.5, 1.5])
        self.assertAlmostEqual(paired[0]["log_ratio"], -math.log(2))
        self.assertAlmostEqual(paired[1]["log_ratio"], math.log(1.5))
        self.assertEqual(audit["valid_pairs"], 2)
        self.assertEqual(audit["nonpositive_or_ineligible_pairs"], 1)
        self.assertEqual(audit["source_mismatch_pairs"], 1)
        self.assertEqual(audit["missing_partner_pairs"], 1)
        self.assertEqual(audit["imputed_pairs"], 0)

    def test_duplicate_quote_is_rejected_instead_of_silently_replaced(self):
        rows = [self.quote("A", "2018-01-05", "maize_purchase_mixed", "2"),
            self.quote("A", "2018-01-05", "maize_purchase_mixed", "3"),
            self.quote("A", "2018-01-05", "urea_domestic", "4")]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "quotes.csv"
            self.write_quotes(path, rows)
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                seasonality.load_quote_pairs(path, ["A"])

    def test_date_mean_uses_mean_logs_and_retains_only_date_level_variance(self):
        # Mean(log ratio) differs from log(mean ratio), and date aggregation
        # removes county dispersion; use y=log_ratio to check actual operation.
        rows = [
            {"county": "A", "date": "2018-01-05", "year": 2018, "month": 1, "log_ratio": 0},
            {"county": "B", "date": "2018-01-05", "year": 2018, "month": 1, "log_ratio": math.log(4)},
            {"county": "A", "date": "2018-02-05", "year": 2018, "month": 2, "log_ratio": math.log(4)},
            {"county": "B", "date": "2018-02-05", "year": 2018, "month": 2, "log_ratio": math.log(4)},
        ]
        aggregated = seasonality.aggregate_dates(rows, "log_ratio")
        self.assertEqual(len(aggregated), 2)
        self.assertAlmostEqual(aggregated[0]["log_ratio"], math.log(2))
        self.assertAlmostEqual(aggregated[1]["log_ratio"], math.log(4))
        result = seasonality.analyze_panel(aggregated, "log_ratio", "panel_equal", include_county=False)
        self.assertAlmostEqual(result["raw_month_r2"], 1)
        self.assertEqual(result["n_observations"], 2)
        self.assertEqual(result["models"]["county_year"]["rank"], 1)

    def test_packaged_baseline_is_a_balanced_unimputed_panel(self):
        path = ROOT / "inputs/normalized_prices.csv"
        if not path.is_file():
            self.skipTest("Full release data are not present in this source-only checkout")
        cohorts = seasonality.load_cohorts(ROOT / "inputs")
        for label, n_counties, n_rows in [("all12", 12, 1296), ("screened6", 6, 648)]:
            with self.subTest(cohort=label):
                paired, audit = seasonality.load_quote_pairs(path, cohorts[label])
                self.assertEqual(len(paired), n_rows)
                self.assertEqual(audit["distinct_dates"], 108)
                self.assertEqual(audit["distinct_counties"], n_counties)
                self.assertEqual(audit["complete_dates"], 108)
                self.assertEqual(audit["imputed_pairs"], 0)

    def test_annual_summaries_distinguish_geometric_and_arithmetic_ratios(self):
        # Ratios 0.5 and 2 have geometric mean 1 and arithmetic mean 1.25;
        # adding county B's two unit ratios changes the group mean to 1.125.
        rows = [
            {"county": "A", "county_name": "A", "date": "2018-01-05", "year": 2018,
                "month": 1, "level_ratio": 0.5, "log_ratio": -math.log(2)},
            {"county": "A", "county_name": "A", "date": "2018-02-05", "year": 2018,
                "month": 2, "level_ratio": 2.0, "log_ratio": math.log(2)},
            {"county": "B", "county_name": "B", "date": "2018-01-05", "year": 2018,
                "month": 1, "level_ratio": 1.0, "log_ratio": 0.0},
            {"county": "B", "county_name": "B", "date": "2018-02-05", "year": 2018,
                "month": 2, "level_ratio": 1.0, "log_ratio": 0.0},
        ]
        summary = seasonality.annual_summaries(rows, "fixture")
        county_a = next(row for row in summary["county"] if row["county"] == "A")
        self.assertAlmostEqual(county_a["mean_log_ratio"], 0)
        self.assertAlmostEqual(county_a["exp_mean_log_ratio"], 1)
        self.assertAlmostEqual(county_a["mean_level_ratio"], 1.25)
        self.assertEqual(county_a["n_pairs"], 2)
        group = summary["cohort"][0]
        self.assertAlmostEqual(group["mean_log_ratio"], 0)
        self.assertAlmostEqual(group["exp_mean_log_ratio"], 1)
        self.assertAlmostEqual(group["mean_level_ratio"], 1.125)
        self.assertEqual(group["n_pairs"], 4)

    def test_cli_writes_results_to_selected_directory_without_changing_input(self):
        # Catches an analysis entry that overwrites normalized input or fails to
        # carry balanced-panel counts and annual mean distinctions to output.
        input_path = ROOT / "inputs/normalized_prices.csv"
        if not input_path.is_file():
            self.skipTest("Full release data are not present in this source-only checkout")
        before = hashlib.sha256(input_path.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            process = subprocess.run([sys.executable, str(ROOT / "code/seasonality_analysis.py"),
                "--output", temporary], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            report = json.loads((Path(temporary) / "seasonality_summary.json").read_text())
            self.assertEqual(report["primary_result"]["n_observations"], 1296)
            self.assertEqual(report["primary_result"]["n_dates"], 108)
            self.assertEqual(len(report["results"]), 12)
            self.assertEqual([row["year"] for row in report["annual_summaries"]["all12"]["cohort"]],
                [2018, 2019, 2020])
        self.assertEqual(hashlib.sha256(input_path.read_bytes()).hexdigest(), before)

    def alert(self, benchmark, observed, g, valid="1"):
        return {"benchmark": benchmark, "cohort": "Full12", "date": observed,
            "N": "12", "valid": valid, "G": str(g)}

    def test_common_calendar_reports_gross_flips_separately_from_net_attainment_change(self):
        # Five common valid dates: one unchanged attained, two losses, one
        # gain, one unchanged not attained. Net=-1 while gross flips=3.
        self.assertTrue(callable(getattr(seasonality, "calendar_comparison", None)),
            "Calendar classification comparison is not implemented")
        rows = [
            self.alert("B0", "2021-01-05", 0), self.alert("B4", "2021-01-05", 0.1),
            self.alert("B0", "2021-01-15", 0.1), self.alert("B4", "2021-01-15", -0.1),
            self.alert("B0", "2021-01-25", -0.1), self.alert("B4", "2021-01-25", 0.1),
            self.alert("B0", "2021-02-05", 0.2), self.alert("B4", "2021-02-05", -0.2),
            self.alert("B0", "2021-02-15", -0.1), self.alert("B4", "2021-02-15", -0.2),
            self.alert("B0", "2021-02-25", "", "0"), self.alert("B4", "2021-02-25", 0.3),
            self.alert("B0", "2021-03-05", 0.4),
        ]
        result = seasonality.calendar_comparison(rows)
        self.assertEqual(result["common_complete_dates"], 5)
        self.assertEqual(result["counts"], {"reference_attained": 3, "alternative_attained": 2,
            "both_attained": 1, "both_not_attained": 1,
            "attained_to_not_attained": 2, "not_attained_to_attained": 1})
        self.assertEqual(result["net_attainment_change"], -1)
        self.assertEqual(result["gross_classification_flips"], 3)
        self.assertAlmostEqual(result["gross_flip_fraction"], 3 / 5)
        self.assertEqual(result["excluded_dates"], ["2021-02-25", "2021-03-05"])
        self.assertEqual(len(result["daily_comparisons"]), 5)

    def test_calendar_attainment_uses_the_frozen_zero_tolerance(self):
        # Exact -1e-12 remains attained under the frozen numerical boundary;
        # a value below it is not attained. Neither is an economic threshold.
        self.assertTrue(callable(getattr(seasonality, "calendar_comparison", None)),
            "Calendar classification comparison is not implemented")
        rows = [self.alert("B0", "2021-01-05", 0),
            self.alert("B4", "2021-01-05", "-1e-12"),
            self.alert("B0", "2021-01-15", "-9.99e-13"),
            self.alert("B4", "2021-01-15", "-1.001e-12")]
        result = seasonality.calendar_comparison(rows)
        self.assertEqual(result["counts"]["reference_attained"], 2)
        self.assertEqual(result["counts"]["alternative_attained"], 1)
        self.assertEqual(result["counts"]["attained_to_not_attained"], 1)

    def test_duplicate_alert_benchmark_dates_are_rejected(self):
        self.assertTrue(callable(getattr(seasonality, "calendar_comparison", None)),
            "Calendar classification comparison is not implemented")
        rows = [self.alert("B0", "2021-01-05", 0),
            self.alert("B0", "2021-01-05", 0.1), self.alert("B4", "2021-01-05", 0)]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            seasonality.calendar_comparison(rows)

    def test_missing_alert_carrier_is_not_fabricated(self):
        self.assertTrue(callable(getattr(seasonality, "load_calendar_comparisons", None)),
            "Optional calendar carrier loading is not implemented")
        with tempfile.TemporaryDirectory() as temporary:
            result = seasonality.load_calendar_comparisons(Path(temporary) / "absent.csv")
        self.assertEqual(result["status"], "NOT_AVAILABLE")
        self.assertEqual(result["comparisons"], [])
        self.assertIsNone(result["source"]["sha256"])

    def test_custom_input_cli_without_alerts_reports_calendar_unavailable(self):
        # A custom input directory must not silently use the canonical alerts
        # carrier from another dataset just because it exists beside the code.
        input_path = ROOT / "inputs/normalized_prices.csv"
        if not input_path.is_file():
            self.skipTest("Full release data are not present in this source-only checkout")
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "custom_inputs"
            required = ["normalized_prices.csv", "original_dictionary/field_dictionary.json",
                "reference_experiments/T1_source/frozen_specification.json",
                "reference_experiments/T4b_source/frozen_retained_cohorts.json"]
            for relative in required:
                target = copied / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / "inputs" / relative, target)
            output = Path(temporary) / "out"
            process = subprocess.run([sys.executable, str(ROOT / "code/seasonality_analysis.py"),
                "--inputs", str(copied), "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            report = json.loads((output / "seasonality_summary.json").read_text())
            self.assertTrue("calendar_comparisons" in report,
                "Optional calendar comparison is not implemented")
            self.assertEqual(report["calendar_comparisons"]["status"], "NOT_AVAILABLE")
            self.assertEqual(report["calendar_comparisons"]["comparisons"], [])
            self.assertEqual(report["primary_result"]["n_observations"], 1296)

    def test_packaged_common_calendar_net_minus_two_has_eighteen_gross_flips(self):
        path = ROOT / "results/alerts/alerts_daily.csv"
        if not path.is_file():
            self.skipTest("Full release alert carrier is not present in this source-only checkout")
        self.assertTrue(callable(getattr(seasonality, "load_calendar_comparisons", None)),
            "Optional calendar carrier loading is not implemented")
        report = seasonality.load_calendar_comparisons(path)
        self.assertEqual(report["status"], "PASS")
        result = report["comparisons"][0]
        self.assertEqual(result["common_complete_dates"], 204)
        self.assertEqual(result["counts"], {"reference_attained": 174, "alternative_attained": 172,
            "both_attained": 164, "both_not_attained": 22,
            "attained_to_not_attained": 10, "not_attained_to_attained": 8})
        self.assertEqual(result["net_attainment_change"], -2)
        self.assertEqual(result["gross_classification_flips"], 18)


if __name__ == "__main__":
    unittest.main()
