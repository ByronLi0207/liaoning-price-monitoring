"""Symmetric county influence checks; a full run reuses archived reference paths."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
REPORT = ROOT / "results/supplementary_validation/county_influence_summary.json"


class CountyInfluenceTests(unittest.TestCase):
    def node_json(self, body):
        if NODE is None:
            self.skipTest("Node.js is required for reference analyses")
        source = "import {COUNTY_IDS,countyColumns,summarizeAlerts} from './code/county_influence.mjs';\n" + body
        process = subprocess.run([NODE, "--input-type=module", "-e", source],
                                 cwd=ROOT, text=True, capture_output=True, check=True)
        return json.loads(process.stdout)

    def test_every_county_is_excluded_once_and_nonmembers_are_rejected(self):
        result = self.node_json("""
          let rejected = false;
          try {countyColumns('not-a-county');} catch(e) {rejected = e instanceof RangeError;}
          console.log(JSON.stringify({ids:COUNTY_IDS, all:countyColumns(), rejected,
            deletions:COUNTY_IDS.map(id=>({id, cols:countyColumns(id)}))}));
        """)
        self.assertTrue(result["rejected"])
        self.assertEqual(len(result["ids"]), 12)
        self.assertEqual(result["all"], list(range(12)))
        self.assertEqual(len(result["deletions"]), 12)
        for excluded, row in enumerate(result["deletions"]):
            self.assertEqual(row["cols"], [i for i in range(12) if i != excluded])

    def test_alerts_start_on_third_date_and_missing_dates_reset_runs(self):
        result = self.node_json("""
          const obs=[true,true,true,false,true,true,true,true].map((valid,i)=>({
            date:String(i+1), valid, G:valid?-1:null, k:valid?6:null,
            source:i<2?'source-a':'source-b'}));
          console.log(JSON.stringify(summarizeAlerts(obs,11)));
        """)
        self.assertEqual(result[0]["dates"], ["3", "7", "8"])
        self.assertEqual(result[0]["episodes"], 2)
        self.assertEqual(result[1]["dates"], ["1", "2", "3", "5", "6", "7", "8"])
        self.assertEqual(result[1]["episodes"], 2)
        self.assertEqual(result[2]["episodes"], 2)
        self.assertEqual(result[1]["required_count"], 4)
        self.assertEqual(result[2]["required_count"], 6)

    @unittest.skipUnless(REPORT.exists(), "Full archived inputs are distributed in the project package")
    def test_saved_results_cover_all_sixty_comparisons_and_match_controls(self):
        report = json.loads(REPORT.read_text())
        rows = report["comparisons"]
        self.assertEqual(report["design"]["R"], 1999)
        self.assertEqual(report["design"]["L"], 6)
        self.assertEqual(len(rows), 65)
        deletions = [r for r in rows if r["excluded_county_id"] is not None]
        self.assertEqual(len(deletions), 60)
        self.assertEqual(len({(r["benchmark"], r["excluded_county_id"]) for r in deletions}), 60)
        classifications = ("strictly_positive", "includes_zero", "strictly_negative", "no_valid_pairs")
        self.assertEqual(sum(report["totals"][key] for key in classifications), 60)
        for key in classifications:
            self.assertEqual(report["totals"][key], sum(r["interval_class"] == key for r in deletions))
            self.assertEqual(report["totals"][key], sum(r.get(key, 0) for r in report["by_benchmark"]))
        self.assertEqual(report["totals"]["strictly_positive"], 53)
        self.assertEqual(report["totals"]["includes_zero"], 7)
        for benchmark in ("B0", "B1", "B2", "B3", "B4"):
            group = [r for r in deletions if r["benchmark"] == benchmark]
            self.assertEqual(len(group), 12)
            self.assertEqual({r["counties"] for r in group}, {11})
            self.assertEqual({r["complete_monitoring_dates"] for r in group}, {204})
            self.assertEqual({r["paired_valid"]+r["paired_invalid"] for r in group}, {1999})
        for check in report["controls"]:
            self.assertEqual(check["control_count_fields"], 1999 * 2 * 7)
            self.assertEqual(check["all_twelve_primary_summary"], "matched")
            self.assertEqual(check["without_Jianping_saved_summary"], "matched")
            self.assertEqual(check["all_twelve_alerts"], "matched")
        primary = json.loads((ROOT / "results/primary_15_L6.json").read_text())
        for actual in [r for r in rows if r["excluded_county_id"] is None]:
            prior = next(r for r in primary if r["benchmark"]==actual["benchmark"] and r["cohort"]=="all12")
            self.assertEqual(actual["condition_count"], prior["condition_count"])
            self.assertEqual(actual["observed_low_count"], prior["observed_low_count"])
            self.assertAlmostEqual(actual["paired_D_mean"], prior["paired_D_mean"], places=12)
            for a, b in zip(actual["paired_D_95"], prior["paired_D_95"]):
                self.assertAlmostEqual(a, b, places=12)
        removed_jianping = next(r for r in rows if r["benchmark"]=="B0" and r["excluded_county_id"]=="211322000000")
        self.assertEqual(removed_jianping["condition_count"], 183)
        self.assertEqual(removed_jianping["observed_low_count"], 259)
        self.assertAlmostEqual(removed_jianping["observed_mean_H"], 259/(183*11), places=12)


if __name__ == "__main__":
    unittest.main()
