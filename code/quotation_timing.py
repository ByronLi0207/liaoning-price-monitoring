"""Recompute quotation persistence and descriptive national/local urea timing.

This diagnostic reads frozen inputs only. It never changes the accepted models,
bootstrap results, source archive, manuscript, or package manifest. All equality
comparisons use original Decimal values. The timing rule is an exploratory,
transparent diagnostic, not a causal model or a standard business-cycle dating
procedure. Run with the same Python runtime used by the replication package.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ("maize_purchase_mixed", "urea_domestic")
SOURCE_TYPES = {
    "ln_price_111": "Liaoning agricultural-price monitoring archive, source-system 111",
    "ln_price_115": "Liaoning agricultural-price monitoring archive, source-system 115",
}


def positive_value(row):
    """Return an eligible original decimal, preserving zero/missing as states."""
    if not row or row.get("status", "observed") != "observed":
        return None
    try:
        value = Decimal(row["value"])
    except (InvalidOperation, KeyError):
        return None
    return value if value.is_finite() and value > 0 else None


def indexed_rows(rows):
    indexed = {}
    for row in rows:
        if row["date"] in indexed:
            raise ValueError(f"duplicate quotation date: {row['date']}")
        indexed[row["date"]] = row
    return indexed


def transition_audit(rows, calendar):
    """One record per scheduled adjacency, including every excluded opportunity."""
    indexed = indexed_rows(rows)
    dates = sorted(calendar)
    if len(set(dates)) != len(dates):
        raise ValueError("duplicate scheduled date")
    output = []
    for previous_date, current_date in zip(dates, dates[1:]):
        previous, current = indexed.get(previous_date), indexed.get(current_date)
        previous_value, current_value = positive_value(previous), positive_value(current)
        positive_pair = previous_value is not None and current_value is not None
        source_boundary = bool(previous and current and
                               previous["source_id"] != current["source_id"])
        if not positive_pair:
            status = "nonpositive_or_missing"
        elif source_boundary:
            status = "source_boundary"
        else:
            status = "valid"
        changed = positive_pair and previous_value != current_value
        output.append({
            "previous_date": previous_date, "date": current_date,
            "previous_value": previous.get("value", "") if previous else "",
            "value": current.get("value", "") if current else "",
            "previous_status": previous.get("status", "") if previous else "absent",
            "status": current.get("status", "") if current else "absent",
            "previous_source_id": previous.get("source_id", "") if previous else "",
            "source_id": current.get("source_id", "") if current else "",
            "previous_raw_record_id": previous.get("raw_record_id", "") if previous else "",
            "raw_record_id": current.get("raw_record_id", "") if current else "",
            "previous_raw_path": previous.get("raw_path", "") if previous else "",
            "raw_path": current.get("raw_path", "") if current else "",
            "positive_pair": positive_pair, "source_boundary": source_boundary,
            "comparison_status": status, "numerical_change": changed,
            "counted_update": status == "valid" and changed,
            "direction": ("up" if current_value > previous_value else "down") if changed else "",
            "percentage_change": float(current_value / previous_value - 1) if changed else None,
        })
    return output


def update_summary(rows, calendar):
    audit = transition_audit(rows, calendar)
    counts = Counter(r["comparison_status"] for r in audit)
    denominator = counts["valid"]
    updates = sum(r["counted_update"] for r in audit)
    return {
        "scheduled_observations": len(calendar),
        "captured_observations": len(rows),
        "positive_observations": sum(positive_value(r) is not None for r in rows),
        "scheduled_transitions": len(audit),
        "excluded_nonpositive_or_missing": counts["nonpositive_or_missing"],
        "excluded_positive_source_boundaries": counts["source_boundary"],
        "valid_same_source_transitions": denominator,
        "updates": updates,
        "unchanged_valid_transitions": denominator - updates,
        "rate": updates / denominator if denominator else None,
        "rate_fraction": f"{updates}/{denominator}" if denominator else None,
    }


def constant_runs(rows, calendar, *, same_source=False):
    """Equal numerical runs; source-boundary splitting is an explicit option."""
    indexed = indexed_rows(rows)
    output, active = [], []

    def close():
        if not active:
            return
        first, last = active[0], active[-1]
        boundaries = sum(a["source_id"] != b["source_id"] for a, b in zip(active, active[1:]))
        output.append({
            "run_type": "same_source" if same_source else "numerical_continuity",
            "start": first["date"], "end": last["date"],
            "observations": len(active),
            "elapsed_days": (date.fromisoformat(last["date"]) - date.fromisoformat(first["date"])).days,
            "value_decimal": str(positive_value(first)),
            "source_ids": "|".join(dict.fromkeys(r["source_id"] for r in active)),
            "source_boundary_count": boundaries,
            "first_raw_record_id": first.get("raw_record_id", ""),
            "last_raw_record_id": last.get("raw_record_id", ""),
            "first_raw_path": first.get("raw_path", ""),
            "last_raw_path": last.get("raw_path", ""),
        })
        active.clear()

    for day in sorted(calendar):
        row = indexed.get(day)
        value = positive_value(row)
        if value is None:
            close()
            continue
        if active and (value != positive_value(active[-1]) or
                       (same_source and row["source_id"] != active[-1]["source_id"])):
            close()
        active.append(row)
    close()
    return output


def month_number(month):
    year, number = map(int, month.split("-"))
    return year * 12 + number - 1


def month_label(number):
    year, zero_based = divmod(number, 12)
    return f"{year:04d}-{zero_based + 1:02d}"


def monthly_national(rows, *, minimum_dekads=2):
    """Equal-weight observed monthly mean, with support and availability retained."""
    grouped = defaultdict(list)
    seen = set()
    for row in rows:
        day = row["nominal_midpoint_date"]
        if day in seen:
            raise ValueError(f"duplicate national nominal date: {day}")
        seen.add(day)
        grouped[day[:7]].append(row)
    first, last = min(map(month_number, grouped)), max(map(month_number, grouped))
    output = []
    for number in range(first, last + 1):
        month = month_label(number)
        observed = sorted(grouped.get(month, []), key=lambda r: r["nominal_midpoint_date"])
        prices, publication_dates = [], []
        for row in observed:
            value = Decimal(row["urea_table_price"])
            if not value.is_finite() or value <= 0:
                raise ValueError(f"invalid national price at {row['nominal_midpoint_date']}")
            prices.append(value)
            publication_dates.append(datetime.strptime(row["body_publication"], "%Y/%m/%d %H:%M").date().isoformat())
        usable = len(prices) >= minimum_dekads
        output.append({
            "month": month,
            "price": sum(prices, Decimal(0)) / len(prices) if usable else None,
            "observed_mean_without_support_filter": sum(prices, Decimal(0)) / len(prices) if prices else None,
            "observed_dekads": len(prices), "expected_nominal_dekads": 3,
            "usable": usable, "complete_three_dekads": len(prices) == 3,
            "available_date": max(publication_dates) if publication_dates else None,
            "nominal_dates": "|".join(r["nominal_midpoint_date"] for r in observed),
            "period_labels": "|".join(r.get("period_label", "") for r in observed),
            "price_unit": "national source table units; percentage timing only",
        })
    return output


def national_turns(months, threshold=Decimal("0.05")):
    """Enumerate ALL reversals, then confirm sustained material new-direction moves.

    A reversal needs contiguous supported months and an immediately preceding
    opposite monthly move. Confirmation needs at least two new-direction moves
    with no flat month/gap and cumulative amplitude >= threshold from the turning
    extreme. A threshold reached after the second move confirms later. Initial
    direction has no observed preceding reversal and creates no event.
    """
    threshold = Decimal(threshold)
    directions = [None] * len(months)
    for i in range(1, len(months)):
        previous, current = months[i - 1], months[i]
        if (previous["price"] is None or current["price"] is None or
                month_number(current["month"]) - month_number(previous["month"]) != 1):
            continue
        delta = current["price"] - previous["price"]
        directions[i] = 1 if delta > 0 else -1 if delta < 0 else 0
    output = []
    for start in range(2, len(months)):
        direction, prior_direction = directions[start], directions[start - 1]
        if direction not in (-1, 1) or prior_direction != -direction:
            continue
        extremum = months[start - 1]
        confirmation, end, count, amplitude = None, start, 0, Decimal(0)
        for j in range(start, len(months)):
            if directions[j] != direction:
                break
            end, count = j, count + 1
            amplitude = abs(months[j]["price"] / extremum["price"] - 1)
            if count >= 2 and amplitude >= threshold and confirmation is None:
                confirmation = j
        confirm_month = months[confirmation] if confirmation is not None else None
        new_direction = "up" if direction == 1 else "down"
        output.append({
            "event_id": f"{int(threshold * 100):02d}pct_{extremum['month']}_{new_direction}",
            "threshold": float(threshold), "turn_month": extremum["month"],
            "direction": new_direction, "turn_price": float(extremum["price"]),
            "first_new_direction_month": months[start]["month"],
            "confirmed": confirmation is not None,
            "confirmation_month": confirm_month["month"] if confirm_month else None,
            "confirmation_available_date": max(m["available_date"] for m in months[start - 1:confirmation + 1]) if confirm_month else None,
            "confirmation_price": float(confirm_month["price"]) if confirm_month else None,
            "consecutive_new_direction_moves": confirmation - start + 1 if confirm_month else count,
            "amplitude": float(abs(confirm_month["price"] / extremum["price"] - 1)) if confirm_month else float(amplitude),
            "direction_run_end_month": months[end]["month"],
            "direction_run_moves": count,
            "direction_run_amplitude": float(amplitude),
            "candidate_status": "confirmed" if confirm_month else "persistence_or_amplitude_not_met",
        })
    return output


def pair_changes(changes, events):
    """Nearest earlier SAME-DIRECTION confirmed event, with no future availability."""
    output = []
    for change in changes:
        eligible = [event for event in events if event["confirmed"] and
                    event["direction"] == change["direction"] and
                    event["confirmation_available_date"] <= change["date"] and
                    event["turn_month"] <= change["date"][:7]]
        matched = max(eligible, key=lambda r: (r["turn_month"], r["confirmation_available_date"])) if eligible else None
        lag = month_number(change["date"][:7]) - month_number(matched["turn_month"]) if matched else None
        confirmation_lag = month_number(change["date"][:7]) - month_number(matched["confirmation_month"]) if matched else None
        output.append({
            **change,
            "event_id": matched["event_id"] if matched else None,
            "national_turn_month": matched["turn_month"] if matched else None,
            "national_confirmation_month": matched["confirmation_month"] if matched else None,
            "national_confirmation_available_date": matched["confirmation_available_date"] if matched else None,
            "lag_months_from_turn": lag,
            "lag_months_from_confirmation": confirmation_lag,
            "within_3_months": lag is not None and 0 <= lag <= 3,
            "within_6_months": lag is not None and 0 <= lag <= 6,
            "within_3_months_of_confirmation": confirmation_lag is not None and 0 <= confirmation_lag <= 3,
            "within_6_months_of_confirmation": confirmation_lag is not None and 0 <= confirmation_lag <= 6,
            "match_status": "matched_prior_confirmed_same_direction" if matched else "no_prior_confirmed_same_direction",
            "prearchive_same_direction_turn_not_observable": matched is None,
        })
    return output


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def plain(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(type(value).__name__)


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"refusing empty diagnostic table: {path.name}")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: str(v) if isinstance(v, Decimal) else v for k, v in row.items()})


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def produce(root=ROOT, output=None):
    output = output or root / "results/benchmark_checks"
    output.mkdir(parents=True, exist_ok=True)
    local_path = root / "inputs/normalized_prices.csv"
    national_path = root / "inputs/full_archive/data/national/nbs_prices.csv"
    dictionary_path = root / "inputs/presentation_dictionary.json"
    calendar_path = root / "inputs/original_dictionary/expected_calendar.csv"
    county_names = {r["zh"]: r["en"] for r in json.loads(dictionary_path.read_text())["entries"] if r["category"] == "county"}
    local = read_csv(local_path)
    calendar = sorted({r["date"] for r in read_csv(calendar_path)})
    grouped = defaultdict(list)
    for row in local:
        if row["region_name"] in county_names and row["product_id"] in PRODUCTS:
            grouped[(row["region_id"], row["region_name"], row["product_id"])].append(row)
    summaries, all_transitions, runs, boundaries, changes = [], [], [], [], []
    for (region_id, county, product), rows in sorted(grouped.items()):
        identity = {"region_id": region_id, "region_name": county,
                    "county": county_names[county], "product_id": product}
        audit = transition_audit(rows, calendar)
        descriptive = constant_runs(rows, calendar)
        same_source = constant_runs(rows, calendar, same_source=True)
        summary = {**identity, **update_summary(rows, calendar),
                   "longest_numerical_run_observations": max(r["observations"] for r in descriptive),
                   "longest_same_source_run_observations": max(r["observations"] for r in same_source)}
        summaries.append(summary)
        for row in audit:
            record = {**identity, **row}
            all_transitions.append(record)
            if row["source_boundary"]:
                previous = next(r for r in rows if r["date"] == row["previous_date"])
                current = next(r for r in rows if r["date"] == row["date"])
                boundaries.append({
                    **record,
                    "previous_source_type": SOURCE_TYPES.get(row["previous_source_id"], row["previous_source_id"]),
                    "source_type": SOURCE_TYPES.get(row["source_id"], row["source_id"]),
                    "previous_source_product_id": previous["source_product_id"],
                    "source_product_id": current["source_product_id"],
                    "previous_endpoint": previous["source_endpoint"],
                    "endpoint": current["source_endpoint"],
                    "unchanged_positive_value_across_boundary": row["positive_pair"] and not row["numerical_change"],
                    "product_name": current["product_name"],
                    "specification": current["specification"], "unit": current["unit"],
                })
            if product == "urea_domestic" and row["counted_update"]:
                changes.append(record)
        runs.extend({**identity, **r} for r in descriptive + same_source)
    medians = {p: median(r["rate"] for r in summaries if r["product_id"] == p) for p in PRODUCTS}
    for row in summaries:
        row["full12_product_median_rate"] = medians[row["product_id"]]
        row["one_third_median_cutoff"] = medians[row["product_id"]] / 3
        row["strictly_below_one_third_median"] = row["rate"] < row["one_third_median_cutoff"]

    national = read_csv(national_path)
    coverage_path = root / "inputs/full_archive/data/national/coverage_rules.json"
    coverage = json.loads(coverage_path.read_text())
    months = monthly_national(national)
    for row in months:
        for label in ("confirmed_cancelled", "unknown_missing", "tail_missing"):
            row[label + "_periods"] = "|".join(p for p in coverage[label] if p[:7] == row["month"])
    candidates, pairs, county_timing = [], [], []
    rule_summaries = []
    for minimum in (2, 3):
        support_months = monthly_national(national, minimum_dekads=minimum)
        month_index = {r["month"]: r for r in support_months}
        for threshold in (Decimal("0.05"), Decimal("0.10")):
            rule = f"min{minimum}_dekads_{int(threshold * 100)}pct"
            events = national_turns(support_months, threshold)
            for row in events:
                row["event_id"] = rule + "_" + row["event_id"]
                row["rule"] = rule
                row["minimum_observed_dekads"] = minimum
            candidates.extend(events)
            paired = pair_changes(changes, events)
            for row in paired:
                row["rule"] = rule
                row["threshold"] = float(threshold)
                row["minimum_observed_dekads"] = minimum
                month = month_index.get(row["date"][:7])
                prior_month = month_index.get(month_label(month_number(row["date"][:7]) - 1))
                latest_available = [m for m in support_months if m["price"] is not None and m["available_date"] <= row["date"]]
                latest = latest_available[-1] if latest_available else None
                row["national_mean_in_local_change_month_retrospective"] = month["price"] if month else None
                row["national_monthly_change_in_local_change_month_retrospective"] = float(month["price"] / prior_month["price"] - 1) if month and prior_month and month["price"] and prior_month["price"] else None
                row["national_change_month_mean_available_date"] = month["available_date"] if month else None
                row["latest_national_month_available_by_local_report_date"] = latest["month"] if latest else None
                row["latest_national_month_mean_available_by_local_report_date"] = latest["price"] if latest else None
            pairs.extend(paired)
            for county, english in county_names.items():
                subset = [r for r in paired if r["region_name"] == county]
                lags = [r["lag_months_from_turn"] for r in subset if r["event_id"] is not None]
                confirmation_lags = [r["lag_months_from_confirmation"] for r in subset if r["event_id"] is not None]
                county_timing.append({
                    "county": english, "region_name": county, "rule": rule,
                    "urea_updates": len(subset), "distinct_urea_update_months": len({r["date"][:7] for r in subset}),
                    "matched_prior_confirmed_same_direction": len(lags),
                    "unmatched_updates": len(subset) - len(lags),
                    "within_3_months_from_turn": sum(r["within_3_months"] for r in subset),
                    "within_6_months_from_turn": sum(r["within_6_months"] for r in subset),
                    "share_all_updates_within_3_months": sum(r["within_3_months"] for r in subset) / len(subset) if subset else None,
                    "share_all_updates_within_6_months": sum(r["within_6_months"] for r in subset) / len(subset) if subset else None,
                    "median_turn_lag_months_among_matched": median(lags) if lags else None,
                    "median_confirmation_lag_months_among_matched": median(confirmation_lags) if confirmation_lags else None,
                    "maximum_turn_lag_months_among_matched": max(lags) if lags else None,
                    "within_3_months_of_confirmation": sum(r["within_3_months_of_confirmation"] for r in subset),
                    "within_6_months_of_confirmation": sum(r["within_6_months_of_confirmation"] for r in subset),
                })
            rule_summaries.append({"rule": rule, "candidate_reversals": len(events),
                                   "confirmed_national_turns": sum(r["confirmed"] for r in events),
                                   "matched_local_updates": sum(r["event_id"] is not None for r in paired),
                                   "total_local_updates": len(paired)})

    output_tables = {
        "quotation_update_rates.csv": summaries,
        "quotation_transition_audit.csv": all_transitions,
        "quotation_constant_runs.csv": runs,
        "quotation_source_boundaries.csv": boundaries,
        "quotation_national_monthly_urea.csv": months,
        "quotation_national_turn_candidates.csv": candidates,
        "quotation_urea_change_pairs.csv": pairs,
        "quotation_county_timing_summary.csv": county_timing,
    }
    for filename, table in output_tables.items():
        write_csv(output / filename, table)
    selected_runs = [r for r in runs if r["county"] in {"Jianping County", "Qingyuan County"} and r["observations"] >= 36]
    jianping_pairs = [r for r in pairs if r["county"] == "Jianping County"]
    summary = {
        "status": "DESCRIPTIVE_DIAGNOSTICS_RECOMPUTED", "input_hashes": {
            str(p.relative_to(root)): sha256(p) for p in (local_path, national_path, dictionary_path, calendar_path, coverage_path)},
        "rules": {
            "update_denominator": "All adjacent scheduled dates with observed positive original decimals at both endpoints and identical source_id; missing/zero/absent endpoints and source boundaries are excluded, without bridging.",
            "numerical_runs": "Observed equal Decimal values at consecutive scheduled slots; same_source runs additionally break at source_id changes. A missing planned slot breaks both definitions.",
            "national_monthly": "Arithmetic mean of observed national urea dekads; principal support >=2 and strict sensitivity support=3; no interpolation or imputation; all support and missing-period categories retained.",
            "turn_candidates": "Every reversal following an immediately preceding opposite monthly move in contiguous supported months; initial direction, flat month and missing support cannot establish/bridge a reversal.",
            "turn_confirmation": "At least two consecutive monthly moves in the new direction and cumulative absolute percentage change from the extreme >=5% (principal) or >=10% (sensitivity); confirmation occurs at first qualifying month.",
            "availability": "Confirmation available date is the latest actual national body-publication date of all monthly data used through confirmation; only events available on/before county monitoring report date are eligible.",
            "pairing": "For each of all source-continuous county urea updates, choose latest earlier same-direction confirmed national turn. Report unlimited descriptive lag AND <=3/<=6-month window counts; unmatched dates have NULL lag.",
            "lag": "Integer calendar-month distance from national extremum month to county update month; confirmation-month distance reported separately; window denominators are ALL local updates, not matched-only.",
            "selection": "Same nationwide rules and all local valid updates for all 12 counties; no six-event or favorable-event selection. Rules designed for this exploratory extension before numerical outcomes were read.",
        },
        "limitations": [
            "National observations start 2017-11-25; Nov 2017 has one dekad and is unsupported. The first principal usable month is Dec 2017. Earlier turning points and preceding directions are not recovered.",
            "Frozen national missing dekads yield observed partial-month means under the principal rule; the strict-three-dekad rule assesses this coverage sensitivity. Unknown missing periods and cancellation labels remain visible.",
            "County monitoring report dates are observed; county publication and underlying transaction times are not observed. This is descriptive date alignment, not a fully real-time information-set study.",
            "The national and county quotations may differ in product specification, survey scope and trading stage. Percentage directions provide context rather than a structural price-transmission estimand.",
            "Latest earlier same-direction pairing can produce long lags and repeated matches to one event; these are weak descriptive associations. Window-restricted counts and all-county controls are essential.",
            "Six Jianping urea updates do not identify a complex timing model, propagation mechanism, causal response or absence of actual transactions.",
            "The end of the national series is right truncated; unconfirmed terminal candidates are retained and cannot be used to explain earlier county changes.",
        ],
        "full12_county_product_update_rates": summaries,
        "selected_long_runs": selected_runs,
        "national_rules_summary": rule_summaries,
        "jianping_all_six_changes_by_rule": jianping_pairs,
        "full12_timing_summary": county_timing,
        "counts": {name: len(rows) for name, rows in output_tables.items()},
        "outputs": {name: sha256(output / name) for name in output_tables},
    }
    (output / "quotation_diagnostics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=plain) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = produce(args.root, args.output)
    print(json.dumps({"status": summary["status"], "counts": summary["counts"],
                      "national_rules_summary": summary["national_rules_summary"]}, indent=2))


if __name__ == "__main__":
    main()
