"""Hand-calculated contracts for quotation adjacency and descriptive timing."""
from decimal import Decimal
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
try:
    import quotation_timing as timing
except ModuleNotFoundError:
    timing = None


def quote(date, value, source="A"):
    return {"date": date, "value": value, "source_id": source,
            "status": "observed" if value else "missing_value",
            "raw_record_id": date, "source_product_id": "p",
            "source_endpoint": "pivot", "region_id": "county",
            "region_name": "County", "product_id": "urea_domestic"}


class QuotationTimingTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(timing, "Quotation timing implementation is required")

    def test_denominator_excludes_both_missing_neighbors_and_source_boundary(self):
        # Five planned comparisons: two valid, two touch missing, one changes source.
        dates = ["2020-01-05", "2020-01-15", "2020-01-25",
                 "2020-02-05", "2020-02-15", "2020-02-25"]
        rows = [quote(d, v, s) for d, v, s in zip(
            dates, ["1", "1.00", "", "1", "1", "2"],
            ["A", "A", "A", "A", "B", "B"])]
        audit = timing.transition_audit(rows, dates)
        self.assertEqual([r["comparison_status"] for r in audit],
                         ["valid", "nonpositive_or_missing", "nonpositive_or_missing",
                          "source_boundary", "valid"])
        summary = timing.update_summary(rows, dates)
        self.assertEqual(summary["scheduled_transitions"], 5)
        self.assertEqual(summary["valid_same_source_transitions"], 2)
        self.assertEqual(summary["updates"], 1)
        self.assertEqual(summary["rate"], 0.5)

    def test_equal_decimal_run_crosses_source_but_missing_observation_breaks_it(self):
        dates = ["2024-01-15", "2024-01-25", "2024-02-05",
                 "2024-02-15", "2024-02-25"]
        rows = [quote(d, v, s) for d, v, s in zip(
            dates, ["1.50", "1.5", "1.50", "", "1.50"],
            ["A", "A", "B", "B", "B"])]
        descriptive = timing.constant_runs(rows, dates, same_source=False)
        self.assertEqual([(r["start"], r["end"], r["observations"])
                          for r in descriptive],
                         [("2024-01-15", "2024-02-05", 3),
                          ("2024-02-25", "2024-02-25", 1)])
        self.assertEqual(descriptive[0]["source_boundary_count"], 1)
        screened = timing.constant_runs(rows, dates, same_source=True)
        self.assertEqual([r["observations"] for r in screened], [2, 1, 1])

    def test_duplicate_dates_are_rejected_instead_of_creating_extra_opportunities(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            timing.transition_audit([quote("2020-01-05", "1"),
                                     quote("2020-01-05", "1")], ["2020-01-05"])

    def test_monthly_average_requires_two_dekads_and_retains_coverage(self):
        rows = [
            {"nominal_midpoint_date": "2020-01-05", "urea_table_price": "100",
             "body_publication": "2020/01/14 09:30", "period_label": "2020-01-上"},
            {"nominal_midpoint_date": "2020-01-25", "urea_table_price": "110",
             "body_publication": "2020/02/04 09:30", "period_label": "2020-01-下"},
            {"nominal_midpoint_date": "2020-02-05", "urea_table_price": "120",
             "body_publication": "2020/02/14 09:30", "period_label": "2020-02-上"},
        ]
        months = timing.monthly_national(rows)
        self.assertEqual(months[0]["price"], Decimal("105"))
        self.assertEqual(months[0]["observed_dekads"], 2)
        self.assertEqual(months[0]["available_date"], "2020-02-04")
        self.assertIsNone(months[1]["price"])
        self.assertEqual(months[1]["observed_dekads"], 1)

    def test_turn_confirmation_requires_two_moves_threshold_and_no_flat_bridge(self):
        # Jan trough is observable after Feb rise, but 5% is first crossed in Apr.
        prices = [110, 100, 102, 104, 106, 105, 100]
        labels = ["2019-12", "2020-01", "2020-02", "2020-03",
                  "2020-04", "2020-05", "2020-06"]
        months = [{"month": m, "price": Decimal(p),
                   "available_date": f"{m}-28"} for m, p in zip(labels, prices)]
        turns = timing.national_turns(months, Decimal("0.05"))
        confirmed = [r for r in turns if r["confirmed"]]
        self.assertEqual([(r["turn_month"], r["direction"], r["confirmation_month"])
                          for r in confirmed],
                         [("2020-01", "up", "2020-04"),
                          ("2020-04", "down", "2020-06")])
        self.assertEqual(confirmed[0]["consecutive_new_direction_moves"], 3)
        self.assertEqual(confirmed[0]["amplitude"], 0.06)
        self.assertEqual(sum(r["confirmed"] for r in timing.national_turns(
            months, Decimal("0.10"))), 0)
        months[3]["price"] = Decimal("102")  # flat month breaks persistence
        self.assertEqual(sum(r["confirmed"] for r in timing.national_turns(
            months, Decimal("0.05"))), 1)

    def test_matching_never_uses_unavailable_future_confirmation(self):
        events = [
            {"event_id": "past", "confirmed": True, "direction": "up",
             "turn_month": "2020-01", "confirmation_month": "2020-04",
             "confirmation_available_date": "2020-05-05"},
            {"event_id": "future", "confirmed": True, "direction": "up",
             "turn_month": "2020-05", "confirmation_month": "2020-07",
             "confirmation_available_date": "2020-08-05"},
        ]
        changes = [{"date": "2020-04-15", "direction": "up"},
                   {"date": "2020-05-15", "direction": "up"}]
        pairs = timing.pair_changes(changes, events)
        self.assertIsNone(pairs[0]["event_id"])
        self.assertIsNone(pairs[0]["lag_months_from_turn"])
        self.assertEqual(pairs[1]["event_id"], "past")
        self.assertEqual(pairs[1]["lag_months_from_turn"], 4)
        self.assertFalse(pairs[1]["within_3_months"])
        self.assertTrue(pairs[1]["within_6_months"])


if __name__ == "__main__":
    unittest.main()
