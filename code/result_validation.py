"""Separate exact discrete validation from portable floating-point validation.

The archived package is checked by SHA-256. Recomputed scientific quantities
are checked by value: integers, labels and missingness match exactly; finite
floating values satisfy abs(actual - expected) <= atol + rtol * abs(expected).
The defaults follow the 1e-12 precision used by the existing validation layer.
Every comparison reports the observed maximum, independently of its threshold.
"""
from __future__ import annotations

import csv
import copy
import hashlib
import io
import math
import re
import struct

ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-12
_INTEGER = re.compile(r"-?[0-9]+\Z")


class ResultMismatch(AssertionError):
    """Recomputed values differ from the accepted scientific quantities."""


def _report():
    return {"status": "PASS", "integer_compared": 0, "categorical_compared": 0,
            "floating_compared": 0, "floating_changed": 0,
            "floating_max_abs_difference": 0.0, "floating_max_relative_difference": 0.0,
            "floating_max_tolerance_fraction": 0.0, "floating_max_abs_path": None,
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "relative_tolerance": RELATIVE_TOLERANCE}


def _metadata_leaf(value, components):
    """Resolve one exact metadata leaf while requiring every parent object."""
    for component in components[:-1]:
        if isinstance(value, dict) and component in value:
            value = value[component]
        elif isinstance(value, list) and type(component) is int and component < len(value):
            value = value[component]
        else:
            raise ResultMismatch("Informational metadata parent differs at " + repr(components))
    last = components[-1]
    if isinstance(value, dict):
        present, leaf = last in value, value.get(last)
    elif isinstance(value, list) and type(last) is int and last < len(value):
        present, leaf = True, value[last]
    else:
        raise ResultMismatch("Informational metadata parent differs at " + repr(components))
    if present and leaf is not None and type(leaf) is not str:
        raise ValueError("Informational paths must identify string or null leaves")
    return present, leaf


def _informational_fields(expected, actual, paths):
    if not isinstance(paths, (tuple, list)):
        raise ValueError("Informational paths must be a sequence of nonempty tuples")
    seen, fields = set(), []
    for components in paths:
        if type(components) is not tuple or not components or any(
                not ((type(part) is str and part and part != "*") or
                     (type(part) is int and part >= 0)) for part in components):
            raise ValueError("Informational paths require exact keys or nonnegative list indices")
        if components in seen:
            raise ValueError("Duplicate informational path")
        seen.add(components)
        left_present, left = _metadata_leaf(expected, components)
        right_present, right = _metadata_leaf(actual, components)
        fields.append({"path": list(components), "expected_present": left_present,
                       "actual_present": right_present, "expected": left, "actual": right})
    return seen, fields


def _compare(expected, actual, path, report, atol, rtol, components=(), informational_paths=frozenset()):
    if components in informational_paths:
        return
    if isinstance(expected, dict):
        optional_keys = {parts[-1] for parts in informational_paths if parts[:-1] == components}
        if not isinstance(actual, dict) or (expected.keys() ^ actual.keys()) - optional_keys:
            raise ResultMismatch("object keys differ at " + path)
        for key in expected:
            child = components + (key,)
            if child not in informational_paths:
                _compare(expected[key], actual[key], path + "/" + str(key), report, atol, rtol,
                         child, informational_paths)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise ResultMismatch("array shape differs at " + path)
        for index, (left, right) in enumerate(zip(expected, actual)):
            _compare(left, right, path + "/" + str(index), report, atol, rtol,
                     components + (index,), informational_paths)
    elif type(expected) is int:
        if type(actual) is not int or expected != actual:
            raise ResultMismatch("integer differs at %s: %r != %r" % (path, expected, actual))
        report["integer_compared"] += 1
    elif type(expected) is float:
        if type(actual) not in (float, int) or not math.isfinite(expected) or not math.isfinite(actual):
            raise ResultMismatch("nonfinite or nonnumeric floating value at " + path)
        difference = abs(actual - expected)
        threshold = atol + rtol * abs(expected)
        relative = difference / abs(expected) if expected else (0.0 if difference == 0 else None)
        if difference > threshold:
            raise ResultMismatch("floating differs at %s: abs=%g > allowed=%g" % (path, difference, threshold))
        report["floating_compared"] += 1
        report["floating_changed"] += int(difference != 0)
        if difference > report["floating_max_abs_difference"]:
            report["floating_max_abs_difference"] = difference
            report["floating_max_abs_path"] = path
        if relative is not None:
            report["floating_max_relative_difference"] = max(report["floating_max_relative_difference"], relative)
        report["floating_max_tolerance_fraction"] = max(
            report["floating_max_tolerance_fraction"], difference / threshold if threshold else 0)
    else:
        if type(actual) is not type(expected) or actual != expected:
            raise ResultMismatch("category or missingness differs at %s: %r != %r" % (path, expected, actual))
        report["categorical_compared"] += 1


def compare_values(expected, actual, *, atol=ABSOLUTE_TOLERANCE, rtol=RELATIVE_TOLERANCE,
                   informational_paths=()):
    """Compare science strictly, with an optional exact-path metadata receipt.

    The caller selects informational string/null leaves for one known artifact.
    The default compares every field. Parent containers, other keys and all
    scientific values keep the ordinary shape and value checks.
    """
    if not math.isfinite(atol) or not math.isfinite(rtol) or atol < 0 or rtol < 0:
        raise ValueError("Comparison tolerances must be finite and nonnegative")
    report = _report()
    report.update(absolute_tolerance=atol, relative_tolerance=rtol)
    paths, fields = _informational_fields(expected, actual, informational_paths)
    if fields:
        report["informational_fields"] = fields
    _compare(expected, actual, "$", report, atol, rtol, informational_paths=paths)
    return report


def compare_exact_bytes(expected, actual):
    if expected != actual:
        raise ResultMismatch("exact byte values differ")
    return {"status": "PASS", "bytes": len(expected), "byte_identity": True,
            "sha256": hashlib.sha256(actual).hexdigest()}


def compare_float64_bytes(expected, actual):
    if len(expected) != len(actual) or len(expected) % 8:
        raise ResultMismatch("float64 shape or encoding differs")
    left = [value[0] for value in struct.iter_unpack("<d", expected)]
    right = [value[0] for value in struct.iter_unpack("<d", actual)]
    report = compare_values(left, right)
    report["byte_identity"] = expected == actual
    return report


def _csv_values(raw, integer_columns, float_columns):
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ResultMismatch("CSV header is missing or duplicated")
    if not integer_columns.issubset(reader.fieldnames):
        raise ResultMismatch("Required integer columns are missing")
    rows = []
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ResultMismatch("CSV column count differs")
        values = {}
        for field, value in row.items():
            if value == "":
                values[field] = None
            elif field in integer_columns:
                if not _INTEGER.fullmatch(value):
                    raise ResultMismatch("CSV integer encoding differs in " + field)
                values[field] = int(value)
            elif (field in float_columns if float_columns is not None else any(marker in value for marker in (".", "e", "E"))):
                try:
                    values[field] = float(value)
                except ValueError:
                    if float_columns is not None:
                        raise ResultMismatch("CSV floating encoding differs in " + field)
                    values[field] = value
            else:
                values[field] = value
        rows.append(values)
    return reader.fieldnames, rows


def compare_csv_bytes(expected, actual, *, integer_columns=frozenset(), float_columns=None):
    floats = set(float_columns) if float_columns is not None else None
    integers = set(integer_columns)
    if floats is not None and integers & floats:
        raise ValueError("CSV integer and floating columns must be disjoint")
    left_header, left = _csv_values(expected, integers, floats)
    right_header, right = _csv_values(actual, integers, floats)
    if left_header != right_header:
        raise ResultMismatch("CSV column order differs")
    report = compare_values(left, right)
    report.update(rows=len(left), byte_identity=expected == actual)
    return report


def compare_values_with_derived_source(expected, actual, *, source_keys,
        expected_source_bytes, actual_source_bytes, integer_columns=frozenset(),
        float_columns=None, informational_paths=()):
    """Verify each recorded source digest, then compare its scientific values.

    A regenerated numerical carrier can differ in final decimal digits. Its
    own digest must still be correct; only that verified digest field is
    normalized when comparing the downstream JSON. All other fields and the
    source CSV remain subject to the ordinary scientific comparison rules.
    """
    left, right = expected, actual
    try:
        for key in source_keys:
            left, right = left[key], right[key]
        left_hash = hashlib.sha256(expected_source_bytes).hexdigest()
        right_hash = hashlib.sha256(actual_source_bytes).hexdigest()
        if left["sha256"] != left_hash or right["sha256"] != right_hash:
            raise ResultMismatch("Recorded derived-source digest does not match its file")
    except (KeyError, TypeError) as error:
        raise ResultMismatch("Derived-source identity metadata is missing") from error
    carrier = compare_csv_bytes(expected_source_bytes, actual_source_bytes,
        integer_columns=integer_columns, float_columns=float_columns)
    normalized_actual = copy.deepcopy(actual)
    source = normalized_actual
    for key in source_keys:
        source = source[key]
    source["sha256"] = left_hash
    report = compare_values(expected, normalized_actual, informational_paths=informational_paths)
    report["derived_source"] = {
        "expected_sha256": left_hash, "actual_sha256": right_hash,
        "recorded_digests_verified": True,
        "byte_identity": expected_source_bytes == actual_source_bytes,
        "scientific_comparison": carrier}
    return report


def validate_alert_summary(summary, cases):
    keys = ("benchmark", "cohort", "rule")
    indexed = {}
    for row in summary:
        identity = tuple(row.get(key) for key in keys)
        if identity in indexed:
            raise ResultMismatch("Duplicate alert configuration")
        indexed[identity] = row
    checked = []
    for case in cases:
        identity = tuple(case[key] for key in keys)
        if identity not in indexed:
            raise ResultMismatch("Missing alert configuration: " + str(identity))
        row = indexed[identity]
        if not case.keys() <= row.keys():
            raise ResultMismatch("Missing alert summary fields")
        checked.append(compare_values(case, {field: row[field] for field in case}))
        expected_percent = case["trigger_dates"] / case["complete_monitoring_dates"] * 100
        if "trigger_percent" not in row:
            raise ResultMismatch("Missing trigger_percent")
        compare_values(float(expected_percent), row["trigger_percent"])
    return {"status": "PASS", "cases_checked": len(checked), "discrete_fields_match": True}
