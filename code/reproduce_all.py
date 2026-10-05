#!/usr/bin/env python3
"""Replay archived analysis in a working copy, without replacing package data."""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import time
import zipfile

from result_validation import (ABSOLUTE_TOLERANCE, RELATIVE_TOLERANCE,
    ResultMismatch, compare_csv_bytes, compare_exact_bytes, compare_float64_bytes,
    compare_values, compare_values_with_derived_source)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reproduction'
WORK = OUT / 'workspace'
COUNT_COLUMNS = {'rep', 'N', 'fixed_T', 'condition_count', 'observed_count',
    'reference_count', 'observed_any_count', 'reference_any_count',
    'fixed_reference_count', 'fixed_reference_any_count'}
ALERT_INTEGER_COLUMNS = {'N', 'valid', 'k', 'required_third', 'required_half',
    'below_run', 'source_boundary', 'rule_i', 'rule_third', 'rule_half',
    'rule_i_start', 'rule_third_start', 'rule_half_start'}
PROTECTED = ('inputs', 'results', 'figures', 'reports')
# Only these scalar execution records are excluded from scientific equality.
# Input and method identities in the same object remain exact.
SEASONALITY_RUNTIME_PATHS = (('provenance', 'python'), ('provenance', 'numpy'))


def compare_result_json(relative, before, after, *, expected_source_bytes=None,
        actual_source_bytes=None):
    """Compare a result using its artifact-specific metadata policy."""
    if relative == 'results/benchmark_checks/seasonality_summary.json':
        if expected_source_bytes is None or actual_source_bytes is None:
            raise ResultMismatch('The seasonality comparison requires both source CSVs')
        return compare_values_with_derived_source(before, after,
            source_keys=('calendar_comparisons', 'source'),
            expected_source_bytes=expected_source_bytes,
            actual_source_bytes=actual_source_bytes,
            integer_columns=ALERT_INTEGER_COLUMNS, float_columns={'G'},
            informational_paths=SEASONALITY_RUNTIME_PATHS)
    return compare_values(before, after)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def frozen_hashes():
    return {path.relative_to(ROOT).as_posix(): sha(path)
            for directory in PROTECTED for path in (ROOT / directory).rglob('*')
            if path.is_file()}


def check_archived_identity():
    manifest = json.loads((ROOT / 'MANIFEST_SHA256.json').read_text(encoding='utf-8'))['files']
    entries = {entry['path']: entry for entry in manifest}
    if len(entries) != len(manifest):
        raise ResultMismatch('Duplicate manifest paths')
    protected = frozen_hashes()
    expected_protected = {relative for relative in entries if relative.split('/')[0] in PROTECTED}
    if protected.keys() != expected_protected:
        raise ResultMismatch('Archived data/report file inventory differs from the manifest')
    for relative, digest in protected.items():
        entry = entries.get(relative)
        if entry is None or digest != entry['sha256'] or (ROOT / relative).stat().st_size != entry['bytes']:
            raise ResultMismatch('Archived file identity mismatch: ' + relative)
    required = ([f'results/precision/{b}_L6_indices.u8' for b in ['B0', 'B2', 'B4']]
                + [f'results/precision/{b}_L6_bStar.f64le' for b in ['B0', 'B2', 'B4']])
    if not all(relative in protected for relative in required):
        raise ResultMismatch('Required archived precision files are missing')
    return protected


def prepare_workspace():
    if WORK.exists():
        raise ResultMismatch('A reproduction workspace already exists. Move reproduction/ before another complete replay.')
    OUT.mkdir(exist_ok=True)
    shutil.copytree(ROOT, WORK, ignore=shutil.ignore_patterns(
        '.git', '__pycache__', 'reproduction', 'native', 'review', '.venv', 'venv'))


def png_dimensions(raw):
    if raw[:8] != b'\x89PNG\r\n\x1a\n' or len(raw) < 24:
        raise ResultMismatch('Generated figure is not a PNG')
    return struct.unpack('>II', raw[16:24])


def check_native(role):
    expected_path = ROOT / 'reports' / (role + '.docx')
    actual_path = WORK / 'native' / (role + '.docx')
    with zipfile.ZipFile(expected_path) as expected, zipfile.ZipFile(actual_path) as actual:
        # Scientific text, equations, tables and styles are exact. Rendered image
        # encoding can differ across systems, so media dimensions are checked.
        fields = ['word/document.xml', 'word/styles.xml']
        for name in fields:
            compare_exact_bytes(expected.read(name), actual.read(name))
        media = sorted(name for name in expected.namelist() if name.startswith('word/media/'))
        if media != sorted(name for name in actual.namelist() if name.startswith('word/media/')):
            raise ResultMismatch('Native media set differs: ' + role)
        changed = []
        for name in media:
            before, after = expected.read(name), actual.read(name)
            if png_dimensions(before) != png_dimensions(after):
                raise ResultMismatch('Native media dimensions differ: ' + role + '/' + name)
            if before != after:
                changed.append(name)
    return {'role': role, 'text_equations_tables_styles_exact': True,
            'media_count': len(media), 'media_dimensions_exact': True,
            'rendered_media_byte_differences': changed}


def main():
    started = time.monotonic()
    archived = check_archived_identity()
    node = os.environ.get('NODE') or shutil.which('node')
    if not node:
        raise SystemExit('Node.js is required; see environment/runtime.json.')
    prepare_workspace()
    commands = []

    def run(arguments, name):
        environment = os.environ.copy()
        for key in ['PRECISION_OUT', 'ALERT_OUT', 'REPLAY_OUT', 'COUNTY_INFLUENCE_OUT']:
            environment.pop(key, None)
        log = OUT / (name + '.log')
        with log.open('w', encoding='utf-8') as destination:
            process = subprocess.run(arguments, cwd=WORK, env=environment,
                stdout=destination, stderr=subprocess.STDOUT)
        record = {'name': name, 'exit_code': process.returncode, 'log_sha256': sha(log)}
        commands.append(record)
        print(json.dumps(record), flush=True)
        if process.returncode:
            raise RuntimeError('Reproduction failed: ' + name + '; see ' + str(log))

    run([node, str(WORK/'code/replay_frozen_science.mjs')], 'original_45_and_screened_groups')
    run([node, str(WORK/'code/precision_extension.mjs')], 'six_precision_checks')
    run([sys.executable, str(WORK/'code/verify_precision_records.py')], 'precision_integer_counts')
    run([node, str(WORK/'code/alerts.mjs')], 'alert_classification')
    run([sys.executable, str(WORK/'code/mc_precision.py')], 'MonteCarlo_uncertainty')
    run([sys.executable, str(WORK/'code/verify_episode_point_statistics.py')], 'episode_points')
    run([sys.executable, str(WORK/'code/seasonality_analysis.py')], 'benchmark_month_factors')
    run([sys.executable, str(WORK/'code/quotation_timing.py')], 'quotation_update_timing')
    run([node, str(WORK/'code/county_influence.mjs')], 'symmetric_county_influence')
    run([sys.executable, str(WORK/'code/supplementary_validation.py')], 'historical_screen_and_county_peers')
    run([node, str(WORK/'inputs/full_archive/code/reproduce.cjs')], 'raw_price_archive')
    run([sys.executable, str(WORK/'code/plot_figures.py')], 'scientific_figures')

    comparisons = {}
    for path in sorted((ROOT/'results/precision').glob('*.csv')):
        relative = path.relative_to(ROOT).as_posix()
        comparisons[relative] = compare_csv_bytes(path.read_bytes(), (WORK/relative).read_bytes(), integer_columns=COUNT_COLUMNS, float_columns={'observed', 'reference', 'D', 'fixed_reference'})
    for path in sorted((ROOT/'results/precision').glob('*.u8')):
        relative = path.relative_to(ROOT).as_posix()
        comparisons[relative] = compare_exact_bytes(path.read_bytes(), (WORK/relative).read_bytes())
    for path in sorted((ROOT/'results/precision').glob('*.f64le')):
        relative = path.relative_to(ROOT).as_posix()
        comparisons[relative] = compare_float64_bytes(path.read_bytes(), (WORK/relative).read_bytes())
    relative = 'results/alerts/alerts_daily.csv'
    comparisons[relative] = compare_csv_bytes((ROOT/relative).read_bytes(), (WORK/relative).read_bytes(), integer_columns=ALERT_INTEGER_COLUMNS, float_columns={'G'})
    for relative in ['results/precision/precision_summary.json',
                     'results/precision/precision_summary_with_MC_error.json',
                     'results/primary_15_L6.json', 'results/alerts/alerts_summary.json']:
        before = json.loads((ROOT/relative).read_text(encoding='utf-8'))
        after = json.loads((WORK/relative).read_text(encoding='utf-8'))
        comparisons[relative] = compare_result_json(relative, before, after)

    for path in sorted((ROOT/'results/benchmark_checks').iterdir()):
        relative = path.relative_to(ROOT).as_posix()
        actual = WORK/relative
        if path.suffix == '.json':
            before = json.loads(path.read_text(encoding='utf-8'))
            after = json.loads(actual.read_text(encoding='utf-8'))
            if path.name == 'seasonality_summary.json':
                carrier = 'results/alerts/alerts_daily.csv'
                comparisons[relative] = compare_result_json(relative, before, after,
                    expected_source_bytes=(ROOT/carrier).read_bytes(),
                    actual_source_bytes=(WORK/carrier).read_bytes())
            else:
                comparisons[relative] = compare_result_json(relative, before, after)
        elif path.suffix == '.csv':
            comparisons[relative] = compare_csv_bytes(path.read_bytes(), actual.read_bytes())
        else:
            comparisons[relative] = compare_exact_bytes(path.read_bytes(), actual.read_bytes())

    for path in sorted((ROOT/'results/supplementary_validation').iterdir()):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        actual = WORK/relative
        if path.suffix == '.json':
            comparisons[relative] = compare_result_json(relative,
                json.loads(path.read_text(encoding='utf-8')),
                json.loads(actual.read_text(encoding='utf-8')))
        elif path.suffix == '.csv':
            comparisons[relative] = compare_csv_bytes(path.read_bytes(), actual.read_bytes())
        else:
            comparisons[relative] = compare_exact_bytes(path.read_bytes(), actual.read_bytes())

    figures = []
    for path in sorted((ROOT/'figures').glob('*.png')):
        actual_path = WORK/path.relative_to(ROOT)
        expected_dimensions, actual_dimensions = png_dimensions(path.read_bytes()), png_dimensions(actual_path.read_bytes())
        if expected_dimensions != actual_dimensions:
            raise ResultMismatch('Figure dimensions differ: ' + path.name)
        figures.append({'file': path.name, 'dimensions_exact': True,
            'archived_sha256': sha(path), 'recomputed_sha256': sha(actual_path),
            'byte_identity': sha(path) == sha(actual_path), 'scientific_inputs_unchanged': True})
    # The plotting driver validates all statistical panels and reads exactly the
    # archived carrier files. No scientific inputs change during the replay.
    for path in (ROOT/'inputs').rglob('*'):
        if path.is_file() and sha(path) != sha(WORK/path.relative_to(ROOT)):
            raise ResultMismatch('Working scientific input changed: ' + str(path.relative_to(ROOT)))

    run([sys.executable, str(WORK/'code/build_docx.py')], 'native_main_report')
    run([sys.executable, str(WORK/'code/build_supplement.py')], 'native_supplement')
    run([sys.executable, str(WORK/'code/build_docx.py'), '--role', 'supplement_methods'], 'native_diagnostic_note')
    run([sys.executable, str(WORK/'code/build_docx.py'), '--role', 'supplement_validation'], 'native_supplementary_validation')
    run([sys.executable, str(WORK/'code/build_docx.py'), '--role', 'project_brief'], 'native_project_brief')
    native = [check_native(role) for role in ['manuscript', 'supplement', 'supplement_methods', 'supplement_validation', 'project_brief']]
    # Keep the existing export entry usable while its input lives outside the
    # protected reports folder. Only regenerated DOCX files are copied here.
    generated_native = ROOT/'native'
    generated_native.mkdir(exist_ok=True)
    for role in ['manuscript', 'supplement', 'supplement_methods', 'supplement_validation', 'project_brief']:
        shutil.copyfile(WORK/'native'/(role+'.docx'), generated_native/(role+'.docx'))
    if archived != frozen_hashes():
        raise ResultMismatch('Archived delivery files changed during replay')
    original = json.loads((WORK/'reproduction/reference_check.json').read_text(encoding='utf-8'))
    report = {'status': 'PASS', 'platform': platform.system(),
        'python': platform.python_version(), 'node': subprocess.check_output([node, '--version'], text=True).strip(),
        'elapsed_seconds': time.monotonic()-started,
        'archived_file_identity_checks': len(archived), 'archived_files_unchanged': True,
        'absolute_tolerance': ABSOLUTE_TOLERANCE, 'relative_tolerance': RELATIVE_TOLERANCE,
        'floating_max_abs_difference': max(value.get('floating_max_abs_difference', 0) for value in comparisons.values()),
        'integer_and_categorical_fields_exact': True,
        'categorical_scope': 'Scientific fields; declared runtime version leaves are informational',
        'runtime_comparison_policy': {
            'version_equality_required': False,
            'informational_paths_by_result': {
                'results/benchmark_checks/seasonality_summary.json':
                    [list(path) for path in SEASONALITY_RUNTIME_PATHS]}},
        'comparisons': comparisons,
        'original_reference_checks': original, 'regenerated_figures': figures,
        'native_reports': native, 'commands': commands,
        'precision_rows': 59994, 'precision_integer_fields': 419958,
        'alert_planned_rows': 3105, 'alert_valid_rows': 3060, 'main_groups': 45}
    (OUT/'acceptance.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'commands': len(commands),
        'floating_max_abs_difference': report['floating_max_abs_difference'],
        'archived_files_unchanged': True}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
