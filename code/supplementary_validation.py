#!/usr/bin/env python3
"""Historical-only quotation screening and matched county-product validation.

The original screen is fitted solely on 2018–2020 observations. Two subsequent
windows describe the fixed membership's outcomes. Peer checks use a fixed set
of eleven other counties and report coverage separately from price movement.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import csv
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
from statistics import median

from quotation_timing import constant_runs, indexed_rows, positive_value, update_summary

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ('maize_purchase_mixed', 'urea_domestic')
WINDOWS = [('historical', '2018-01-05', '2020-12-25'),
           ('validation_2021_2023', '2021-01-05', '2023-12-25'),
           ('validation_2024_2026', '2024-01-05', '2026-09-25')]


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def window_update_summary(rows, calendar, start, end):
    days = [day for day in calendar if start <= day <= end]
    return update_summary([row for row in rows if start <= row['date'] <= end], days)


def long_runs(rows, calendar):
    return [run for run in constant_runs(rows, calendar, same_source=True)
            if run['observations'] > 36]


def below_median_fraction(updates, denominator, rate_pairs):
    if not denominator or any(not total for _, total in rate_pairs):
        return None
    cutoff = median(Fraction(count, total) for count, total in rate_pairs) / 3
    return Fraction(updates, denominator) < cutoff


def national_window(rows, product, start, end, cutoff, calendar):
    field = {'maize_purchase_mixed': 'maize_table_price', 'urea_domestic': 'urea_table_price'}[product]
    selected, late = {}, 0
    for row in rows:
        day = row['nominal_midpoint_date']
        if not start <= day <= end:
            continue
        publication = datetime.strptime(row['body_publication'], '%Y/%m/%d %H:%M').date().isoformat()
        if publication > cutoff:
            late += 1
            continue
        value = Decimal(row[field])
        if value.is_finite() and value > 0:
            if day in selected:
                raise ValueError('Duplicate national endpoint: ' + day)
            selected[day] = value
    values = list(selected.values())
    expected = sum(start <= day <= end for day in calendar)
    amplitude = max(values) / min(values) - 1 if values else None
    return {'expected_national_dates': expected, 'observed_national_dates': len(values),
            'national_coverage': len(values) / expected if expected else None,
            'excluded_late_publications': late,
            'first_national_date': min(selected) if selected else None,
            'last_national_date': max(selected) if selected else None,
            'amplitude': float(amplitude) if amplitude is not None else None,
            'above_twenty_percent': amplitude > Decimal('0.20') if amplitude is not None else False,
            'full_calendar_coverage': len(values) == expected and expected > 0}


def year_on_year(rows, start, end):
    index = indexed_rows(rows)
    changes, boundary, unavailable = [], 0, 0
    for day in sorted(index):
        if not start <= day <= end:
            continue
        previous_day = str(int(day[:4]) - 1) + day[4:]
        previous, current = index.get(previous_day), index[day]
        before, after = positive_value(previous), positive_value(current)
        if before is None or after is None:
            unavailable += 1
        elif previous['source_id'] != current['source_id']:
            boundary += 1
        else:
            changes.append(float(after / before - 1))
    return {'same_source_pairs': len(changes), 'excluded_source_boundaries': boundary,
            'unavailable_pairs': unavailable,
            'median_percentage_change': median(changes) if changes else None,
            'median_absolute_percentage_change': median(abs(v) for v in changes) if changes else None,
            'zero_change_pairs': sum(v == 0 for v in changes)}


def price_amplitudes(rows, start, end):
    grouped = defaultdict(list)
    for row in rows:
        value = positive_value(row)
        if start <= row['date'] <= end and value is not None:
            grouped[row['source_id']].append(value)
    return [{'source_id': source, 'observations': len(values),
             'amplitude': float(max(values) / min(values) - 1)}
            for source, values in sorted(grouped.items())]


def peer_window(rows, calendar, target, product, counties, start, end):
    peers = [county for county in counties if county != target]
    if len(peers) != len(set(peers)) or target not in counties:
        raise ValueError('Peer county membership must be unique and include target')
    days = [day for day in calendar if start <= day <= end]
    grouped = defaultdict(list)
    for row in rows:
        if row['region_id'] in peers and row['product_id'] == product:
            grouped[row['region_id']].append(row)
    indices = {county: indexed_rows(grouped[county]) for county in peers}
    daily, median_values, observed = [], [], 0
    for day in days:
        values = [positive_value(indices[county].get(day)) for county in peers]
        values = [value for value in values if value is not None]
        observed += len(values)
        complete = len(values) == len(peers) and bool(peers)
        middle = median(values) if complete else None
        if complete:
            median_values.append(middle)
        daily.append({'date': day, 'available_peers': len(values),
                      'complete_peer_membership': complete,
                      'fixed_peer_median': str(middle) if middle is not None else None})
    updating, valid_transitions = 0, 0
    for county in peers:
        update = window_update_summary(grouped[county], days, start, end)
        updating += update['updates'] > 0
        valid_transitions += update['valid_same_source_transitions']
    expected = len(peers) * len(days)
    return {'peer_count': len(peers), 'planned_dates': len(days),
            'observed_peer_quotes': observed, 'expected_peer_quotes': expected,
            'peer_quote_coverage': observed / expected if expected else None,
            'complete_peer_dates': len(median_values),
            'complete_peer_date_coverage': len(median_values) / len(days) if days else None,
            'minimum_available_peers': min((row['available_peers'] for row in daily), default=None),
            'complete_peer_median_amplitude': float(max(median_values) / min(median_values) - 1) if median_values else None,
            'peers_with_any_update': updating,
            'pooled_valid_peer_transitions': valid_transitions,
            'daily': daily}


def screen_history(rows, calendar, national, counties, start=WINDOWS[0][1], end=WINDOWS[0][2]):
    selected = [row for row in rows if row['region_id'] in counties]
    grouped = defaultdict(list)
    for row in selected:
        grouped[(row['region_id'], row['product_id'])].append(row)
    days = [day for day in calendar if start <= day <= end]
    rates = {(county, product): window_update_summary(grouped[(county, product)], days, start, end)
             for county in counties for product in PRODUCTS}
    evidence, detail = [], []
    for county in counties:
        product_status = []
        for product in PRODUCTS:
            update = rates[(county, product)]
            pair_rates = [(rates[(peer, product)]['updates'], rates[(peer, product)]['valid_same_source_transitions'])
                          for peer in counties]
            low = below_median_fraction(update['updates'], update['valid_same_source_transitions'], pair_rates)
            product_runs = long_runs([row for row in grouped[(county, product)] if start <= row['date'] <= end], days)
            run_flag, incomplete_run = False, False
            for run in product_runs:
                national_result = national_window(national, product, run['start'], run['end'], end, calendar)
                run_flag |= national_result['above_twenty_percent']
                incomplete_run |= not national_result['full_calendar_coverage'] and not national_result['above_twenty_percent']
                detail.append({'county': county, 'product_id': product, **run, **national_result})
            if low or run_flag:
                status = 'flagged'
            elif low is None or incomplete_run:
                status = 'unresolved'
            else:
                status = 'not_flagged'
            cutoff = median(Fraction(count, total) for count, total in pair_rates) / 3 if all(total for _, total in pair_rates) else None
            evidence.append({'county': county, 'product_id': product, **update,
                             'historical_start': start, 'historical_end': end,
                             'median_one_third_threshold': float(cutoff) if cutoff is not None else None,
                             'low_update_flag': low, 'long_run_count': len(product_runs),
                             'national_run_flag': run_flag, 'classification': status})
            product_status.append(status)
    county_status = {}
    for county in counties:
        states = [row['classification'] for row in evidence if row['county'] == county]
        county_status[county] = 'flagged' if 'flagged' in states else 'unresolved' if 'unresolved' in states else 'not_flagged'
    return {'historical_start': start, 'historical_end': end,
            'county_classification': county_status,
            'flagged_counties': [county for county in counties if county_status[county] == 'flagged'],
            'not_flagged_counties': [county for county in counties if county_status[county] == 'not_flagged'],
            'unresolved_counties': [county for county in counties if county_status[county] == 'unresolved'],
            'nonflagged_membership_including_unresolved': [county for county in counties if county_status[county] != 'flagged'],
            'product_evidence': evidence, 'run_evidence': detail}


def alert_validation(rows, calendar, counties, selected, start, end):
    index = {(row['region_id'], row['date'], row['product_id']): row for row in rows}
    baseline = {}
    for county in counties:
        values = []
        for day in calendar:
            if not WINDOWS[0][1] <= day <= WINDOWS[0][2]:
                continue
            maize, urea = [positive_value(index.get((county, day, product))) for product in PRODUCTS]
            if maize is None or urea is None:
                raise ValueError('Historical paired panel is incomplete')
            values.append(math.log(float(maize)) - math.log(float(urea)))
        baseline[county] = math.fsum(values) / len(values)
    complete, attained, aggregate_alerts, half_alerts = 0, 0, 0, 0
    run_length = 0
    for day in calendar:
        if day < WINDOWS[1][1]:
            continue
        values = {}
        for county in counties:
            product_rows = [index.get((county, day, product)) for product in PRODUCTS]
            maize, urea = [positive_value(row) for row in product_rows]
            if maize is not None and urea is not None and product_rows[0]['source_id'] == product_rows[1]['source_id']:
                values[county] = math.log(float(maize)) - math.log(float(urea)) - baseline[county]
        valid = len(values) == len(counties) and bool(selected)
        if valid:
            mean = math.fsum(values[county] for county in selected) / len(selected)
            run_length = run_length + 1 if mean < -1e-12 else 0
        else:
            run_length = 0
        if not start <= day <= end:
            continue
        if valid:
            complete += 1
            attained += mean >= -1e-12
            aggregate_alerts += run_length >= 3
            half_alerts += 2 * sum(values[county] < -1e-12 for county in selected) >= len(selected)
    return {'counties': len(selected), 'complete_dates': complete,
            'attainment_dates': attained, 'attainment_rate': attained / complete if complete else None,
            'aggregate_three_date_alerts': aggregate_alerts,
            'common_half_share_alerts': half_alerts,
            'aggregate_alert_rate': aggregate_alerts / complete if complete else None}


def group_summaries(validation, flagged, nonflagged):
    summaries = []
    keys = sorted({(row['window'], row['product_id']) for row in validation})
    for window, product in keys:
        for label, counties in [('historically_flagged', flagged),
                                ('historically_unflagged_including_unresolved', nonflagged)]:
            panel = [row for row in validation if row['window'] == window
                     and row['product_id'] == product and row['county'] in counties]
            updates = sum(row['updates'] for row in panel)
            denominator = sum(row['valid_same_source_transitions'] for row in panel)
            rates = [row['rate'] for row in panel if row['rate'] is not None]
            summaries.append({'window': window, 'product_id': product, 'membership': label,
                              'counties': len(counties), 'counties_with_valid_transitions': len(rates),
                              'updates': updates, 'valid_same_source_transitions': denominator,
                              'pooled_update_rate': updates / denominator if denominator else None,
                              'median_county_update_rate': median(rates) if rates else None,
                              'counties_with_long_run': sum(row['long_runs_over_36'] > 0 for row in panel),
                              'long_runs_over_36': sum(row['long_runs_over_36'] for row in panel)})
    return summaries


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (list, dict)) else value
                             for key, value in row.items()})


def produce(root=ROOT, output=None):
    root = Path(root)
    output = Path(output) if output else root / 'results/supplementary_validation'
    output.mkdir(parents=True, exist_ok=True)
    paths = {'local': root / 'inputs/normalized_prices.csv',
             'national': root / 'inputs/full_archive/data/national/nbs_prices.csv',
             'calendar': root / 'inputs/original_dictionary/expected_calendar.csv',
             'membership': root / 'inputs/reference_experiments/T1_source/frozen_specification.json'}
    counties = json.loads(paths['membership'].read_text())['main_codes']
    if len(counties) != 12 or len(set(counties)) != 12:
        raise ValueError('Original county set is not twelve distinct counties')
    rows = [row for row in read_csv(paths['local']) if row['region_id'] in counties and row['product_id'] in PRODUCTS]
    calendar = sorted({row['date'] for row in read_csv(paths['calendar'])})
    national = read_csv(paths['national'])
    names = {row['region_id']: row['region_name'] for row in rows}
    screen = screen_history(rows, calendar, national, counties)
    validation = []
    for label, start, end in WINDOWS:
        for county in counties:
            for product in PRODUCTS:
                series = [row for row in rows if row['region_id'] == county and row['product_id'] == product]
                days = [day for day in calendar if start <= day <= end]
                values = [row for row in series if start <= row['date'] <= end]
                runs = constant_runs(values, days, same_source=True)
                validation.append({'window': label, 'start': start, 'end': end, 'county': county,
                                   'county_name': names[county], 'product_id': product,
                                   'historical_county_classification': screen['county_classification'][county],
                                   **window_update_summary(series, calendar, start, end),
                                   'longest_same_source_run': max((run['observations'] for run in runs), default=0),
                                   'long_runs_over_36': sum(run['observations'] > 36 for run in runs),
                                   'same_source_window_amplitudes': price_amplitudes(series, start, end),
                                   **year_on_year(series, start, end)})
    frozen_nonflagged = screen['nonflagged_membership_including_unresolved']
    alerts = [{'window': label, 'start': start, 'end': end, 'membership': member_label,
               **alert_validation(rows, calendar, counties, subset, start, end)}
              for label, start, end in WINDOWS[1:]
              for member_label, subset in [('all_twelve', counties), ('historically_unflagged_including_one_unresolved', frozen_nonflagged)]]
    validation_groups = group_summaries(validation, screen['flagged_counties'], frozen_nonflagged)
    peer_results, peer_daily = [], []
    for county in counties:
        for product in PRODUCTS:
            series = [row for row in rows if row['region_id'] == county and row['product_id'] == product]
            for number, run in enumerate(long_runs(series, calendar), 1):
                result = peer_window(rows, calendar, county, product, counties, run['start'], run['end'])
                daily = result.pop('daily')
                identity = {'county': county, 'county_name': names[county], 'product_id': product, 'run_number': number}
                peer_results.append({**identity, **run, **result})
                peer_daily += [{**identity, **row} for row in daily]
    pair_index = {(row['region_id'], row['date'], row['product_id']): row for row in rows}
    complete_days = []
    for day in calendar:
        complete = True
        for county in counties:
            pair = [pair_index.get((county, day, product)) for product in PRODUCTS]
            if any(positive_value(row) is None for row in pair) or pair[0]['source_id'] != pair[1]['source_id']:
                complete = False
                break
        if complete:
            complete_days.append(day)
    window_mask = {'definition': 'Original twelve counties all-positive same-source price-pair calendar',
                   'windows': [{'window': label, 'start': start, 'end': end,
                                'planned_dates': sum(start <= day <= end for day in calendar),
                                'complete_dates': sum(start <= day <= end for day in complete_days),
                                'missing_dates': [day for day in calendar if start <= day <= end and day not in complete_days]}
                               for label, start, end in WINDOWS]}
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
    temporal_summary = {'status': 'PASS', 'input_sha256': hashes,
                        'fitting_window': [WINDOWS[0][1], WINDOWS[0][2]],
                        'screen': screen, 'validation': validation, 'validation_groups': validation_groups, 'alerts': alerts,
                        'alert_benchmark': {'key': 'B0', 'years': '2018–2020',
                                            'definition': 'Each county mean log maize/urea ratio on 108 historical dates'},
                        'window_mask': window_mask,
                        'rules': {'update_fraction': 'strictly below original twelve-county product median / 3',
                                  'run_length': 'strictly greater than 36 scheduled observations, same source',
                                  'national_amplitude': 'strictly greater than 20%, publication available by historical end',
                                  'future_policy': 'Later local and national data are excluded from fitting',
                                  'membership': 'Confirmed historical flags are removed; unresolved cases are identified and included in nonflagged membership',
                                  'alerts': 'Original twelve-county common completeness mask; historical per-county mean log ratios; carry three-date condition over validation window boundary; reset at missing scheduled date'}}
    peer_summary = {'status': 'PASS', 'input_sha256': hashes,
                    'long_constant_runs': len(peer_results),
                    'runs_with_peer_median_amplitude_above_twenty_percent': sum(row['complete_peer_median_amplitude'] is not None and row['complete_peer_median_amplitude'] > 0.20 for row in peer_results),
                    'runs_with_any_updating_peer': sum(row['peers_with_any_update'] > 0 for row in peer_results),
                    'runs': peer_results,
                    'rules': {'target': 'All same-source constant runs >36 observations for both products and all twelve original counties',
                              'peer_membership': 'Other eleven original counties, same exact product/specification/unit',
                              'median': 'Only dates with positive observed quotations for all eleven fixed peers; coverage shown separately',
                              'peer_changes': 'Same-source adjacent scheduled observations inside the target run, no missing bridging',
                              'coverage': 'Observed peer quotation cells / (11 x planned dates), plus complete-peer-date coverage'}}
    outputs = [('temporal_screen_summary.json', temporal_summary), ('peer_summary.json', peer_summary)]
    for filename, value in outputs:
        (output / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    for filename, value in [('temporal_screen_products.csv', screen['product_evidence']),
                            ('temporal_screen_runs.csv', screen['run_evidence']),
                            ('temporal_screen_validation.csv', validation),
                            ('temporal_screen_alerts.csv', alerts),
                            ('temporal_screen_validation_groups.csv', validation_groups),
                            ('peer_runs.csv', peer_results), ('peer_daily.csv', peer_daily)]:
        write_csv(output / filename, value)
    rules = ('Temporal screening uses only 2018–2020 local observations and national nominal endpoints within each historical run, with publication available by 25 December 2020.\n'
             'Thresholds are unchanged: update rate < product median / 3; same-source constant run >36 observations AND observed national amplitude >20%.\n'
             'National partial coverage with subthreshold movement remains unresolved. Product branches combine by OR; confirmed flags fix membership before two later validation windows.\n'
             'Updates and runs do not bridge missing/nonpositive values or source changes. Windows have independent denominators and exact decimal equality.\n'
             'Year-on-year changes pair the same product and date slot only within the same source. Window amplitudes are reported separately by source.\n'
             'Peer medians exclude the target and use all eleven fixed other counties on complete-peer dates. Quotation-cell and complete-date coverage are reported separately.\n'
             'Peer update counts use same-source scheduled adjacencies internal to each target run.\n')
    (output / 'temporal_screen_peer_rules.txt').write_text(rules, encoding='utf-8')
    return {'output': str(output), 'historical_flags': screen['flagged_counties'],
            'historical_unresolved': screen['unresolved_counties'], 'peer_runs': len(peer_results), 'alerts': alerts}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(produce(args.root, args.output), ensure_ascii=False, indent=2))
