#!/usr/bin/env python3
"""Descriptive month-factor decomposition of the frozen 2018–2020 baseline.

This entry reads the packaged input and writes new benchmark_checks files.
It performs no imputation, forecasting, causal inference, or scientific replay.
Only NumPy and the Python standard library are required.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import platform

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
START, END = "2018-01-05", "2020-12-25"
PRODUCTS = {"maize_purchase_mixed": "混等收购价", "urea_domestic": "国产"}
METHOD_SOURCES = [
    "https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html",
    "https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.rsquared.html",
]


def load_cohorts(inputs):
    """Read original memberships; do not select counties using new outcomes."""
    inputs = Path(inputs)
    main = json.loads((inputs / "reference_experiments/T1_source/frozen_specification.json").read_text())
    screened = json.loads((inputs / "reference_experiments/T4b_source/frozen_retained_cohorts.json").read_text())
    if main["baseline"] != [START, END]:
        raise ValueError("Archived baseline differs from the strict 2018–2020 window")
    cohorts = {"all12": main["main_codes"], "screened6": next(
        row["retained"] for row in screened["cohorts"] if row["set_id"] == "complete_set_3")}
    if (len(set(cohorts["all12"])) != 12 or len(cohorts["all12"]) != 12
            or len(set(cohorts["screened6"])) != 6 or len(cohorts["screened6"]) != 6
            or not set(cohorts["screened6"]).issubset(cohorts["all12"])):
        raise ValueError("Archived cohort membership is invalid")
    return cohorts


def load_quote_pairs(path, county_codes, start=START, end=END):
    """Use published positive pairs, exact specifications/units and same source."""
    selected = set(county_codes)
    if not selected or len(selected) != len(county_codes):
        raise ValueError("County cohort must be nonempty and contain unique codes")
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValueError("Invalid analysis window")
    quotes = defaultdict(dict)
    records = 0
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {"region_id", "region_name", "date", "product_id", "specification",
            "value", "unit", "source_id", "analysis_eligible"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Canonical input fields are missing")
        for row in reader:
            if row["region_id"] not in selected or row["product_id"] not in PRODUCTS:
                continue
            observed = date.fromisoformat(row["date"])
            if not first <= observed <= last:
                continue
            if row["specification"] != PRODUCTS[row["product_id"]] or row["unit"] != "元/500克":
                raise ValueError("Unexpected target-product specification or unit")
            key = (row["region_id"], observed.isoformat())
            if row["product_id"] in quotes[key]:
                raise ValueError("Duplicate canonical quote: " + "|".join([*key, row["product_id"]]))
            quotes[key][row["product_id"]] = row
            records += 1
    audit = {"input_quote_records_in_window_and_cohort": records,
        "candidate_county_dates": len(quotes), "valid_pairs": 0,
        "nonpositive_or_ineligible_pairs": 0, "source_mismatch_pairs": 0,
        "missing_partner_pairs": 0, "imputed_pairs": 0}
    paired = []
    for (county, observed), products in sorted(quotes.items(), key=lambda item: (item[0][1], item[0][0])):
        if any(product not in products for product in PRODUCTS):
            audit["missing_partner_pairs"] += 1
            continue
        maize, urea = products["maize_purchase_mixed"], products["urea_domestic"]
        try:
            maize_value, urea_value = float(maize["value"]), float(urea["value"])
        except ValueError:
            maize_value = urea_value = math.nan
        if (not all(math.isfinite(value) and value > 0 for value in [maize_value, urea_value])
                or any(row["analysis_eligible"].lower() != "true" for row in [maize, urea])):
            audit["nonpositive_or_ineligible_pairs"] += 1
            continue
        source_fields = ["source_id"]
        if "source_system_id" in maize and "source_system_id" in urea:
            source_fields.append("source_system_id")
        if any(maize[field] != urea[field] for field in source_fields):
            audit["source_mismatch_pairs"] += 1
            continue
        parsed = date.fromisoformat(observed)
        paired.append({"county": county, "county_name": maize["region_name"],
            "date": observed, "year": parsed.year, "month": parsed.month,
            "day": parsed.day, "source_id": maize["source_id"],
            "maize_quote": maize_value, "urea_quote": urea_value,
            "log_ratio": math.log(maize_value) - math.log(urea_value),
            "level_ratio": maize_value / urea_value})
    counts = Counter(row["date"] for row in paired)
    planned = [date(year, month, day).isoformat()
        for year in range(first.year, last.year + 1) for month in range(1, 13)
        for day in [5, 15, 25] if first <= date(year, month, day) <= last]
    audit.update({"valid_pairs": len(paired), "distinct_dates": len(counts),
        "distinct_counties": len({row["county"] for row in paired}),
        "expected_monitoring_dates": len(planned),
        "complete_dates": sum(counts[observed] == len(selected) for observed in planned),
        "missing_complete_dates": [observed for observed in planned if counts[observed] != len(selected)],
        "county_count_per_observed_date": dict(sorted(counts.items())),
        "source_ids": sorted({row["source_id"] for row in paired}),
        "start": min(counts) if counts else None, "end": max(counts) if counts else None})
    return paired, audit


def aggregate_dates(rows, outcome):
    """Arithmetic mean of the selected outcome per date; no log retransformation."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["date"]].append(row)
    return [{"county": "__date_mean__", "date": observed,
        "year": group[0]["year"], "month": group[0]["month"],
        outcome: math.fsum(row[outcome] for row in group) / len(group),
        "contributing_counties": len(group)} for observed, group in sorted(grouped.items())]


def _design(rows, factors):
    columns = [np.ones(len(rows))]
    labels = ["Intercept"]
    references = {}
    for factor in factors:
        levels = sorted({row[factor] for row in rows})
        references[factor] = levels[0]
        for level in levels[1:]:
            columns.append(np.array([float(row[factor] == level) for row in rows]))
            labels.append(f"{factor}[{level}]")
    return np.column_stack(columns), labels, references


def analyze_panel(rows, outcome, weighting="panel_equal", include_county=True):
    """Nested least-squares decomposition on an identical sample and weights.

    M: intercept + month; CY: intercept + county + year;
    CYM: intercept + county + year + month. Date means omit county.
    Weighted least squares here sets the descriptive population emphasis;
    it makes no inverse-variance or independent-error inference.
    """
    if not rows:
        raise ValueError("Cannot analyze an empty panel")
    if len({(row["county"], row["date"]) for row in rows}) != len(rows):
        raise ValueError("Duplicate county-date in model sample")
    y = np.array([row[outcome] for row in rows], dtype=float)
    if not np.all(np.isfinite(y)):
        raise ValueError("Model outcome must be finite")
    date_counts = Counter(row["date"] for row in rows)
    if weighting == "panel_equal":
        weights = np.ones(len(rows))
    elif weighting == "date_equal":
        weights = np.array([1.0 / date_counts[row["date"]] for row in rows])
    else:
        raise ValueError("Unknown weighting: " + weighting)
    weight_sum = float(weights.sum())
    mean_y = float(np.dot(weights, y) / weight_sum)
    centered = y - mean_y
    tss = float(np.dot(weights, centered * centered))
    # A tolerance relative to centered TSS handles exact fits; large levels of
    # y cannot incorrectly erase real small variation around a large mean.
    zero_sse_tolerance = 64 * np.finfo(float).eps * tss
    root_weights = np.sqrt(weights)
    controls = (["county"] if include_county else []) + ["year"]
    factors = {"month": ["month"], "county_year": controls,
        "county_year_month": controls + ["month"]}
    models = {}
    for name, terms in factors.items():
        design, labels, references = _design(rows, terms)
        weighted_design = design * root_weights[:, None]
        rcond = np.finfo(float).eps * max(weighted_design.shape)
        coefficients, _, rank, singular = np.linalg.lstsq(
            weighted_design, centered * root_weights, rcond=rcond)
        residual = centered - design @ coefficients
        sse = float(np.dot(weights, residual * residual))
        if sse <= zero_sse_tolerance:
            sse = 0.0
        coefficients[0] += mean_y
        models[name] = {"formula": outcome + " ~ 1 + " + " + ".join(terms),
            "rank": int(rank), "design_columns": design.shape[1],
            "residual_degrees_of_freedom": len(rows) - int(rank),
            "rank_deficient": int(rank) < design.shape[1],
            "reference_levels": references, "sse": sse,
            "r2": (1 - sse / tss) if tss > 0 else None,
            "column_labels": labels, "coefficients": coefficients.tolist(),
            "singular_values": singular.tolist(), "lstsq_rcond": rcond}
    reduced_sse = models["county_year"]["sse"]
    added_sse = reduced_sse - models["county_year_month"]["sse"]
    if added_sse < -zero_sse_tolerance:
        raise ArithmeticError("Nested full model has materially larger SSE")
    if abs(added_sse) <= zero_sse_tolerance:
        added_sse = 0.0
    status = "DEFINED"
    if tss == 0:
        status = "ZERO_TOTAL_VARIANCE"
    elif reduced_sse == 0:
        status = "ZERO_REDUCED_RESIDUAL_VARIANCE"
    return {"n_observations": len(rows), "n_dates": len(date_counts),
        "n_counties": len({row["county"] for row in rows}) if include_county else None,
        "weighting": weighting, "weight_formula": "1" if weighting == "panel_equal" else "1/n_t",
        "weight_sum": weight_sum, "outcome": outcome, "outcome_mean": mean_y,
        "include_county_control": include_county, "tss": tss,
        "zero_sse_tolerance": zero_sse_tolerance, "models": models,
        "raw_month_r2": models["month"]["r2"],
        "incremental_month_r2": added_sse / tss if tss > 0 else None,
        "partial_month_r2": added_sse / reduced_sse if reduced_sse > 0 else None,
        "month_sse_reduction": added_sse,
        "month_rank_increment": models["county_year_month"]["rank"] - models["county_year"]["rank"],
        "variance_status": status}


def annual_summaries(rows, cohort):
    """Equal county-date descriptive means within each calendar year."""
    by_county = defaultdict(list)
    by_year = defaultdict(list)
    for row in rows:
        by_county[(row["county"], row["year"])].append(row)
        by_year[row["year"]].append(row)

    def summary(group):
        mean_log = math.fsum(row["log_ratio"] for row in group) / len(group)
        return {"n_pairs": len(group), "n_dates": len({row["date"] for row in group}),
            "n_counties": len({row["county"] for row in group}),
            "mean_log_ratio": mean_log, "exp_mean_log_ratio": math.exp(mean_log),
            "mean_level_ratio": math.fsum(row["level_ratio"] for row in group) / len(group)}

    county = [{"cohort": cohort, "county": code, "county_name": group[0]["county_name"],
        "year": year, **summary(group)} for (code, year), group in sorted(by_county.items())]
    group = [{"cohort": cohort, "year": year, **summary(values)}
        for year, values in sorted(by_year.items())]
    return {"weighting": "Each valid county-date pair has equal weight",
        "county": county, "cohort": group}


def calendar_comparison(rows, reference="B0", alternative="B4", cohort="Full12"):
    """Compare attainment on intersected complete dates, retaining both flows.

    The frozen condition is G >= -1e-12. Net changes count gains minus losses;
    gross flips count gains plus losses. A missing date is never classified.
    """
    panel = {reference: {}, alternative: {}}
    tolerance = 1e-12
    for row in rows:
        if row["cohort"] != cohort or row["benchmark"] not in panel:
            continue
        benchmark = row["benchmark"]
        observed = date.fromisoformat(row["date"]).isoformat()
        if observed in panel[benchmark]:
            raise ValueError("Duplicate benchmark-cohort-date: " + "|".join([benchmark, cohort, observed]))
        if int(row["N"]) != 12 or row["valid"] not in ["0", "1"]:
            raise ValueError("Calendar comparison requires a twelve-county 0/1 validity carrier")
        valid = row["valid"] == "1"
        g = float(row["G"]) if valid else None
        if valid and not math.isfinite(g):
            raise ValueError("A complete calendar date must contain finite G")
        panel[benchmark][observed] = {"valid": valid, "G": g,
            "source_signature": row.get("source_signature")}
    if not all(panel.values()):
        raise ValueError("Calendar carrier does not contain both target benchmark series")
    valid_dates = {benchmark: {observed for observed, row in values.items() if row["valid"]}
        for benchmark, values in panel.items()}
    common = sorted(valid_dates[reference] & valid_dates[alternative])
    daily = []
    transitions = Counter()
    for observed in common:
        before, after = panel[reference][observed], panel[alternative][observed]
        if (before["source_signature"] is not None and after["source_signature"] is not None
                and before["source_signature"] != after["source_signature"]):
            raise ValueError("Common calendar date has different source signatures")
        old_attained, new_attained = before["G"] >= -tolerance, after["G"] >= -tolerance
        if old_attained and new_attained:
            transition = "both_attained"
        elif not old_attained and not new_attained:
            transition = "both_not_attained"
        elif old_attained:
            transition = "attained_to_not_attained"
        else:
            transition = "not_attained_to_attained"
        transitions[transition] += 1
        daily.append({"cohort": cohort, "date": observed, "reference_benchmark": reference,
            "alternative_benchmark": alternative, "reference_G": before["G"],
            "alternative_G": after["G"], "reference_attained": old_attained,
            "alternative_attained": new_attained, "transition": transition,
            "classification_changed": old_attained != new_attained})
    counts = {"reference_attained": transitions["both_attained"] + transitions["attained_to_not_attained"],
        "alternative_attained": transitions["both_attained"] + transitions["not_attained_to_attained"],
        **{label: transitions[label] for label in ["both_attained", "both_not_attained",
            "attained_to_not_attained", "not_attained_to_attained"]}}
    net = counts["alternative_attained"] - counts["reference_attained"]
    gross = counts["attained_to_not_attained"] + counts["not_attained_to_attained"]
    denominator = len(common)
    return {"status": "PASS" if common else "NO_COMMON_COMPLETE_DATES", "cohort": cohort, "N": 12,
        "reference_benchmark": reference, "alternative_benchmark": alternative,
        "reference_definition": "Full 2018–2020 county-specific mean(log Q)",
        "alternative_definition": "Same-calendar-month 2018–2020 county-specific mean(log Q)",
        "attainment_condition": "G >= -1e-12", "numerical_tolerance": tolerance,
        "common_complete_dates": denominator, "first_common_date": common[0] if common else None,
        "last_common_date": common[-1] if common else None,
        "scheduled_dates_by_benchmark": {key: len(value) for key, value in panel.items()},
        "complete_dates_by_benchmark": {key: len(value) for key, value in valid_dates.items()},
        "excluded_dates": sorted((set(panel[reference]) | set(panel[alternative])) - set(common)),
        "counts": counts, "net_attainment_change": net, "gross_classification_flips": gross,
        "net_change_formula": "gains - losses = alternative_attained - reference_attained",
        "gross_flip_formula": "gains + losses",
        "gross_flip_fraction": gross / denominator if denominator else None,
        "net_change_percentage_points": 100 * net / denominator if denominator else None,
        "flip_dates": [row["date"] for row in daily if row["classification_changed"]],
        "daily_comparisons": daily}


def load_calendar_comparisons(path):
    """Read an optional archived carrier; absence has no invented counts."""
    path = Path(path)
    try:
        displayed_path = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        displayed_path = str(path.resolve())
    report = {"schema": "benchmark_calendar_comparison_v1", "status": "NOT_AVAILABLE",
        "source": {"path": displayed_path, "sha256": None}, "comparisons": []}
    if not path.is_file():
        report["reason"] = "Optional archived alerts_daily.csv is absent; no calendar comparison was computed"
        return report
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not {"benchmark", "cohort", "date", "N", "valid", "G"}.issubset(reader.fieldnames or []):
            raise ValueError("Alert carrier fields are missing")
        comparison = calendar_comparison(list(reader))
    report.update({"status": comparison["status"], "comparisons": [comparison]})
    report["source"]["sha256"] = _sha(path)
    if comparison["common_complete_dates"]:
        report["english_results_paragraph"] = (
            f"On the {comparison['common_complete_dates']} common complete monitoring dates for all twelve counties, "
            f"the full 2018–2020 and same-month benchmarks classified "
            f"{comparison['counts']['reference_attained']} and {comparison['counts']['alternative_attained']} "
            f"dates as attained, respectively. This net change of {comparison['net_attainment_change']} dates "
            f"combines {comparison['counts']['attained_to_not_attained']} dates changing from attained to not attained "
            f"and {comparison['counts']['not_attained_to_attained']} changing in the opposite direction. "
            f"In total, {comparison['gross_classification_flips']} dates "
            f"({100 * comparison['gross_flip_fraction']:.2f}%) changed classification. "
            f"The net difference therefore understates the number of date-specific classification changes.")
    return report


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ranges(rows):
    return {name: [min(row[name] for row in rows), max(row[name] for row in rows)]
        for name in ["raw_month_r2", "incremental_month_r2", "partial_month_r2"]}


def build_report(inputs, alerts_path=None):
    inputs = Path(inputs)
    cohorts = load_cohorts(inputs)
    results, audits, annual = [], {}, {}
    for cohort, counties in cohorts.items():
        pairs, audit = load_quote_pairs(inputs / "normalized_prices.csv", counties)
        if (audit["valid_pairs"] != len(counties) * 108 or audit["complete_dates"] != 108
                or audit["start"] != START or audit["end"] != END):
            raise ValueError("Frozen baseline is not the expected complete 108-date panel: " + cohort)
        audits[cohort] = audit
        annual[cohort] = annual_summaries(pairs, cohort)
        for outcome in ["log_ratio", "level_ratio"]:
            for weighting in ["panel_equal", "date_equal"]:
                result = analyze_panel(pairs, outcome, weighting)
                result.update({"cohort": cohort, "aggregation": "county_date_panel"})
                results.append(result)
            mean_result = analyze_panel(aggregate_dates(pairs, outcome), outcome, include_county=False)
            mean_result.update({"cohort": cohort, "aggregation": "date_mean",
                "weighting": "date_mean_equal", "weight_formula": "1 per date mean",
                "contributing_counties": len(counties)})
            results.append(mean_result)
    primary = next(row for row in results if row["cohort"] == "all12"
        and row["outcome"] == "log_ratio" and row["weighting"] == "panel_equal")
    panel = [row for row in results if row["aggregation"] == "county_date_panel"]
    log_range = _ranges([row for row in panel if row["outcome"] == "log_ratio"])
    level_range = _ranges([row for row in panel if row["outcome"] == "level_ratio"])
    weight_diffs = []
    for cohort in cohorts:
        for outcome in ["log_ratio", "level_ratio"]:
            a, b = [next(row for row in panel if row["cohort"] == cohort
                and row["outcome"] == outcome and row["weighting"] == weighting)
                for weighting in ["panel_equal", "date_equal"]]
            weight_diffs.append({"cohort": cohort, "outcome": outcome,
                "max_absolute_r2_difference": max(abs(a[field] - b[field]) for field in log_range)})
    screened = next(row for row in panel if row["cohort"] == "screened6"
        and row["outcome"] == "log_ratio" and row["weighting"] == "panel_equal")
    english = (
        f"In the complete 2018–2020 baseline (12 counties, 108 monitoring dates, "
        f"{primary['n_observations']:,} county–date pairs), calendar-month indicators explained "
        f"{100 * primary['raw_month_r2']:.2f}% of the pooled variation in log maize/urea ratios. "
        f"After county and year effects were included, adding month indicators increased R-squared "
        f"by {100 * primary['incremental_month_r2']:.2f} percentage points and explained "
        f"{100 * primary['partial_month_r2']:.2f}% of the remaining variance (partial R-squared). "
        f"For the frozen screened six-county group, the corresponding values were "
        f"{100 * screened['raw_month_r2']:.2f}%, {100 * screened['incremental_month_r2']:.2f} "
        f"percentage points, and {100 * screened['partial_month_r2']:.2f}%. "
        f"Equal-date weighting gave the same results, because both baseline panels were balanced. "
        f"Using the level ratio instead of its log gave raw month R-squared values of "
        f"{100 * level_range['raw_month_r2'][0]:.2f}–{100 * level_range['raw_month_r2'][1]:.2f}% "
        f"and partial values of {100 * level_range['partial_month_r2'][0]:.2f}–"
        f"{100 * level_range['partial_month_r2'][1]:.2f}%. "
        f"These are in-sample descriptive associations; they neither identify causal seasonal "
        f"effects nor demonstrate forecasting performance.")
    provenance_paths = ["normalized_prices.csv", "original_dictionary/field_dictionary.json",
        "reference_experiments/T1_source/frozen_specification.json",
        "reference_experiments/T4b_source/frozen_retained_cohorts.json"]
    calendar = load_calendar_comparisons(alerts_path if alerts_path is not None
        else inputs.resolve().parent / "results/alerts/alerts_daily.csv")
    return {"schema": "descriptive_month_factor_v1", "status": "PASS",
        "window": {"start": START, "end": END, "years": [2018, 2019, 2020],
            "expected_dates": 108, "strict_inclusive_slice": True, "interpolation": "none"},
        "definition": {"Q": "maize_purchase_mixed quote / urea_domestic quote, same county/date/source/unit",
            "primary_outcome": "log(Q)=log(maize)-log(urea)",
            "sensitivity_outcome": "Q in levels",
            "B0_correspondence": "County-specific mean(log(Q)) over the 108 baseline dates; exp(mean(log(Q))) is the geometric mean of Q, not mean(Q)",
            "B4_correspondence": "County-specific month-specific mean(log(Q)) in the same baseline; the shared-month model here is a descriptive diagnostic, not a replication of all county-by-month B4 coefficients",
            "raw_month_r2": "1-SSE(month)/centered_TSS",
            "incremental_month_r2": "[SSE(county+year)-SSE(county+year+month)]/centered_TSS",
            "partial_month_r2": "[SSE(county+year)-SSE(county+year+month)]/SSE(county+year)",
            "date_mean_controls": "Year and month only; county effects are unavailable after aggregation",
            "date_equal_weights": "Each county-date row has weight 1/n_t, giving each monitoring date total weight one",
            "scope": "Descriptive in-sample fit only; no causal effect, forecast validation, or independent-error claim"},
        "provenance": {"input_hashes": {name: _sha(inputs / name) for name in provenance_paths},
            "baseline_core_path": "code/reference_core.js", "baseline_core_sha256": _sha(ROOT / "code/reference_core.js"),
            "analysis_path": "code/seasonality_analysis.py", "analysis_sha256": _sha(__file__),
            "test_path": "tests/test_seasonality_analysis.py", "test_sha256": _sha(ROOT / "tests/test_seasonality_analysis.py"),
            "python": platform.python_version(), "numpy": np.__version__, "method_sources": METHOD_SOURCES,
            "reproduce_command": "python3 code/seasonality_analysis.py",
            "test_command": "python3 -m unittest discover -s tests -p test_seasonality_analysis.py -v"},
        "cohort_codes": cohorts, "sample_audits": audits, "primary_result": primary,
        "results": results, "robustness": {"panel_log_ratio": log_range,
            "panel_level_ratio": level_range, "panel_both_transforms": _ranges(panel),
            "date_mean_log_ratio": _ranges([row for row in results
                if row["aggregation"] == "date_mean" and row["outcome"] == "log_ratio"]),
            "equal_date_vs_equal_pair_checks": weight_diffs},
        "annual_summaries": annual, "english_results_paragraph": english,
        "calendar_comparisons": calendar}


def write_report(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "seasonality_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    columns = ["cohort", "aggregation", "outcome", "weighting", "n_observations", "n_dates",
        "n_counties", "raw_month_r2", "incremental_month_r2", "partial_month_r2",
        "month_rank", "county_year_rank", "full_rank", "month_rank_increment", "tss",
        "month_sse", "county_year_sse", "full_sse"]
    with (output / "seasonality_models.csv").open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=columns)
        writer.writeheader()
        for result in report["results"]:
            values = {field: result[field] for field in columns if field in result}
            values.update({"month_rank": result["models"]["month"]["rank"],
                "county_year_rank": result["models"]["county_year"]["rank"],
                "full_rank": result["models"]["county_year_month"]["rank"],
                "month_sse": result["models"]["month"]["sse"],
                "county_year_sse": result["models"]["county_year"]["sse"],
                "full_sse": result["models"]["county_year_month"]["sse"]})
            writer.writerow(values)
    annual_columns = ["scope", "cohort", "county", "county_name", "year", "n_pairs",
        "n_dates", "n_counties", "mean_log_ratio", "exp_mean_log_ratio", "mean_level_ratio"]
    with (output / "seasonality_annual.csv").open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=annual_columns)
        writer.writeheader()
        for summary in report["annual_summaries"].values():
            for scope in ["county", "cohort"]:
                for row in summary[scope]:
                    writer.writerow({"scope": scope, **row})
    calendar_columns = ["cohort", "N", "reference_benchmark", "alternative_benchmark",
        "common_complete_dates", "reference_attained", "alternative_attained", "both_attained",
        "both_not_attained", "attained_to_not_attained", "not_attained_to_attained",
        "net_attainment_change", "gross_classification_flips", "gross_flip_fraction",
        "net_change_percentage_points", "first_common_date", "last_common_date"]
    daily_columns = ["cohort", "date", "reference_benchmark", "alternative_benchmark",
        "reference_G", "alternative_G", "reference_attained", "alternative_attained",
        "transition", "classification_changed"]
    comparisons = report["calendar_comparisons"]["comparisons"]
    with (output / "seasonality_calendar_comparisons.csv").open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=calendar_columns)
        writer.writeheader()
        for comparison in comparisons:
            flattened = {**comparison, **comparison["counts"]}
            writer.writerow({key: flattened[key] for key in calendar_columns})
    with (output / "seasonality_calendar_dates.csv").open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=daily_columns)
        writer.writeheader()
        for comparison in comparisons:
            for row in comparison["daily_comparisons"]:
                writer.writerow({key: int(value) if isinstance(value, bool) else value
                    for key, value in row.items()})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=ROOT / "inputs")
    parser.add_argument("--output", type=Path, default=ROOT / "results/benchmark_checks")
    parser.add_argument("--alerts", type=Path, default=None,
        help="Optional archived alerts CSV; default is results/alerts/alerts_daily.csv beside the selected inputs directory")
    args = parser.parse_args(argv)
    report = build_report(args.inputs, args.alerts)
    write_report(report, args.output)
    print(json.dumps({"status": report["status"], "models": len(report["results"]),
        "raw_month_r2": report["primary_result"]["raw_month_r2"],
        "incremental_month_r2": report["primary_result"]["incremental_month_r2"],
        "partial_month_r2": report["primary_result"]["partial_month_r2"],
        "calendar_comparison_status": report["calendar_comparisons"]["status"],
        "output": str(args.output)}, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
