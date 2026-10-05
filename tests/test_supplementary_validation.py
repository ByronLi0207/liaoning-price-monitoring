"""Fixtures exercise historical-only screening and matched peer histories."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
try:
    import supplementary_validation as analysis
except ImportError:
    analysis = None


def quotation(day, county='a', value='1', source='s', product='urea_domestic'):
    return {'date': day, 'region_id': county, 'region_name': county,
            'product_id': product, 'value': value, 'source_id': source,
            'status': 'observed', 'analysis_eligible': 'True'}


def national(day, value, published=None):
    return {'nominal_midpoint_date': day, 'urea_table_price': value,
            'maize_table_price': value,
            'body_publication': (published or day.replace('-', '/')) + ' 09:00'}


class SupplementaryValidationFixtures(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(analysis, 'supplementary validation module has not been implemented')

    def test_run_threshold_is_strict_and_does_not_join_sources_or_missing_slots(self):
        days = [f'2020-{m:02d}-{d:02d}' for m in range(1, 13) for d in (5, 15, 25)] + ['2021-01-05']
        rows = [quotation(day) for day in days]
        self.assertEqual(len(analysis.long_runs(rows[:36], days[:36])), 0)
        self.assertEqual(analysis.long_runs(rows, days)[0]['observations'], 37)
        switched = [dict(row, source_id='t') if i >= 20 else row for i, row in enumerate(rows)]
        self.assertEqual(analysis.long_runs(switched, days), [])
        self.assertEqual(analysis.long_runs(rows[:20] + rows[21:], days), [])

    def test_window_update_denominator_excludes_entering_and_source_transitions(self):
        days = ['2019-12-25', '2020-01-05', '2020-01-15', '2020-01-25']
        rows = [quotation(days[0], value='5'), quotation(days[1]),
                quotation(days[2], value='2'), quotation(days[3], value='3', source='t')]
        result = analysis.window_update_summary(rows, days, '2020-01-05', '2020-01-25')
        self.assertEqual(result['valid_same_source_transitions'], 1)
        self.assertEqual(result['updates'], 1)
        self.assertEqual(result['excluded_positive_source_boundaries'], 1)

    def test_national_window_rejects_future_nominal_and_publication_dates(self):
        rows = [national('2020-01-05', '100'), national('2020-01-15', '130'),
                national('2020-01-25', '900', '2021/01/05'), national('2021-01-05', '1000')]
        result = analysis.national_window(rows, 'urea_domestic', '2020-01-05',
                                          '2020-01-25', '2020-12-25', ['2020-01-05','2020-01-15','2020-01-25'])
        self.assertAlmostEqual(result['amplitude'], 0.3)
        self.assertEqual(result['observed_national_dates'], 2)
        self.assertEqual(result['expected_national_dates'], 3)
        self.assertEqual(result['excluded_late_publications'], 1)

    def test_peer_median_excludes_target_and_uses_only_complete_fixed_membership(self):
        days = ['2020-01-05', '2020-01-15', '2020-01-25']
        rows = [quotation(day, 'a', '1000') for day in days]
        rows += [quotation(days[0], 'b', '1'), quotation(days[1], 'b', '2'), quotation(days[2], 'b', '3')]
        rows += [quotation(days[0], 'c', '3'), quotation(days[1], 'c', '4')]
        result = analysis.peer_window(rows, days, 'a', 'urea_domestic', ['a','b','c'], days[0], days[-1])
        self.assertEqual(result['peer_count'], 2)
        self.assertEqual(result['complete_peer_dates'], 2)
        self.assertAlmostEqual(result['complete_peer_median_amplitude'], 0.5)
        self.assertEqual(result['peers_with_any_update'], 2)
        self.assertEqual(result['observed_peer_quotes'], 5)
        self.assertEqual(result['expected_peer_quotes'], 6)

    def test_update_rate_flag_is_strict_one_third_of_original_median(self):
        self.assertFalse(analysis.below_median_fraction(1, 9, [(1,3),(1,3),(1,3)]))
        self.assertTrue(analysis.below_median_fraction(1, 10, [(1,3),(1,3),(1,3)]))

    def test_same_source_year_on_year_does_not_bridge_switch_or_missing(self):
        rows = [quotation('2019-01-05', value='1'), quotation('2020-01-05', value='2'),
                quotation('2019-01-15', value='1'), quotation('2020-01-15', value='3', source='t')]
        result = analysis.year_on_year(rows, '2020-01-05', '2020-12-25')
        self.assertEqual(result['same_source_pairs'], 1)
        self.assertEqual(result['excluded_source_boundaries'], 1)
        self.assertEqual(result['median_percentage_change'], 1.0)

    def test_fixed_membership_summary_pools_opportunities_and_reports_county_median(self):
        rows = [{'window':'later', 'product_id':'urea_domestic', 'county':'a', 'updates':1,
                 'valid_same_source_transitions':10, 'rate':0.1, 'long_runs_over_36':1},
                {'window':'later', 'product_id':'urea_domestic', 'county':'b', 'updates':2,
                 'valid_same_source_transitions':2, 'rate':1.0, 'long_runs_over_36':0}]
        self.assertTrue(hasattr(analysis, 'group_summaries'), 'group summary has not been implemented')
        result = analysis.group_summaries(rows, ['a','b'], [])
        flagged = next(row for row in result if row['membership'] == 'historically_flagged')
        self.assertEqual(flagged['updates'], 3)
        self.assertEqual(flagged['valid_same_source_transitions'], 12)
        self.assertEqual(flagged['pooled_update_rate'], 0.25)
        self.assertEqual(flagged['median_county_update_rate'], 0.55)

    @unittest.skipUnless((ROOT / 'inputs/normalized_prices.csv').exists(), 'Full input is provided with the release')
    def test_later_local_and_national_mutations_do_not_change_historical_membership(self):
        rows = analysis.read_csv(ROOT / 'inputs/normalized_prices.csv')
        national_rows = analysis.read_csv(ROOT / 'inputs/full_archive/data/national/nbs_prices.csv')
        calendar = sorted({row['date'] for row in analysis.read_csv(ROOT / 'inputs/original_dictionary/expected_calendar.csv')})
        counties = json.loads((ROOT / 'inputs/reference_experiments/T1_source/frozen_specification.json').read_text())['main_codes']
        expected = analysis.screen_history(rows, calendar, national_rows, counties)
        mutated_local = [dict(row, value='100000') if row['date'] > '2020-12-25' else row for row in rows]
        mutated_national = [dict(row, urea_table_price='1000000', maize_table_price='1000000')
                            if row['nominal_midpoint_date'] > '2020-12-25' else row for row in national_rows]
        self.assertEqual(analysis.screen_history(mutated_local, calendar, mutated_national, counties), expected)

    @unittest.skipUnless((ROOT / 'results/supplementary_validation/peer_summary.json').exists(), 'Full results are provided with the release')
    def test_release_peer_and_temporal_results_match_fixed_scientific_counts(self):
        folder = ROOT / 'results/supplementary_validation'
        peer = json.loads((folder / 'peer_summary.json').read_text())
        temporal = json.loads((folder / 'temporal_screen_summary.json').read_text())
        self.assertEqual(peer['long_constant_runs'], 20)
        self.assertEqual(peer['runs_with_any_updating_peer'], 20)
        self.assertEqual(peer['runs_with_peer_median_amplitude_above_twenty_percent'], 3)
        self.assertEqual(temporal['screen']['flagged_counties'],
                         ['210111000000','210423000000','210882000000','211121000000','211322000000'])
        self.assertEqual(temporal['screen']['unresolved_counties'], ['210124000000'])
        self.assertEqual([row['complete_dates'] for row in temporal['alerts']], [106,106,98,98])
        self.assertEqual([row['aggregate_three_date_alerts'] for row in temporal['alerts']], [13,12,6,4])


if __name__ == '__main__':
    unittest.main()
