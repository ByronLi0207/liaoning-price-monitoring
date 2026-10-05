#!/usr/bin/env python3

"""Scientific figure data and rendering helpers."""

import sys

import argparse, base64, copy, hashlib, json, re, subprocess, tempfile, warnings, zipfile

from pathlib import Path

from html.parser import HTMLParser

from datetime import datetime

from xml.etree import ElementTree as ET

import numpy as np

import matplotlib

import matplotlib.pyplot as plt

import matplotlib.dates as mdates

from matplotlib.lines import Line2D

from PIL import Image

from docx import Document

from docx.shared import Cm, Pt

from docx.oxml import OxmlElement

from docx.oxml.ns import qn

from docx.enum.text import WD_ALIGN_PARAGRAPH

from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

from pypdf import PdfReader

matplotlib.use("Agg")

COHORTS = ("all12", "without_Jianping11", "without_Jianping_Qingyuan10")

BENCHMARKS = ("B0", "B1", "B2", "B3", "B4")

EXPECTED_CORE_SHA = "2898d3c9a348886cf990cdfa2373fae38a9a520c6736f255233b6690c4efc6d8"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

class InertJSON(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.active = False
        self.current_id = None
        self.buf = []
        self.scripts = {}
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("type") == "application/json":
            self.active = True
            self.current_id = a.get("id")
            self.buf = []
    def handle_endtag(self, tag):
        if tag == "script" and self.active:
            if self.current_id in self.scripts:
                raise ValueError("Duplicate JSON script ID")
            self.scripts[self.current_id] = "".join(self.buf)
            self.active = False
    def handle_data(self, data):
        if self.active:
            self.buf.append(data)

def carrier(input_dir, spec):
    path = input_dir / spec["filename"]
    raw = path.read_bytes()
    if sha(raw) != spec["carrier_sha256"]:
        raise ValueError("Carrier SHA mismatch: " + spec["filename"])
    html = raw.decode("utf-8", errors="strict")
    parser = InertJSON()
    parser.feed(html)
    if spec["script_id"] not in parser.scripts:
        raise ValueError("Expected inert JSON script absent: " + spec["filename"])
    return json.loads(parser.scripts[spec["script_id"]])

def validate_t1(summary):
    keys = [(r["benchmark"], r["cohort"], r["L"]) for r in summary]
    expected = {(b, c, L) for b in BENCHMARKS for c in COHORTS for L in (3, 6, 12)}
    if len(keys) != 45 or set(keys) != expected:
        raise ValueError("T1 must retain all45 original configurations")
    for r in summary:
        if r["R"] != 1999 or r["fixed_reference_valid"] != 1999 or r["paired_valid"] != 1999:
            raise ValueError("T1 valid repetition count changed")
        exact = r["observed_low_count"] / (r["counties"] * r["condition_count"])
        if abs(exact - r["observed_mean_H"]) > 1e-12:
            raise ValueError("T1 H denominator mismatch")
    return {(r["benchmark"], r["cohort"]): r for r in summary if r["L"] == 6}

def validate_t4b(summary):
    if len(summary) != 20 or len({(r["benchmark"], r["set_id"]) for r in summary}) != 20:
        raise ValueError("Expected five benchmarks by four complete screening sets")
    for r in summary:
        n = r["counties"]
        if n == 0:
            fields = ("condition_count", "observed_mean_H", "fixed_reference_mean",
                      "fixed_reference_p", "paired_D_mean")
            if any(r.get(k) is not None for k in fields) or r["paired_D_95"] != [None, None]:
                raise ValueError("EMPTY_COHORT must retain NA, never zero")
            if r["paired_valid"] != 0 or r["paired_invalid"] != 1999:
                raise ValueError("Explicit empty skip count mismatch")
        elif n == 1:
            if not (r["observed_mean_H"] == r["fixed_reference_mean"] == r["paired_D_mean"] == 0
                    and r["fixed_reference_p"] == 1 and r["paired_D_95"] == [0, 0]
                    and r["paired_D_positive_fraction"] == 0 and r["paired_valid"] == 1999):
                raise ValueError("One-county centered conditional statistic must be degenerate")
        elif n in (4, 6):
            if r["paired_valid"] != 1999:
                raise ValueError("T4b valid count mismatch")
        else:
            raise ValueError("Unexpected complete retained-cohort size")
    return {"configurations": 20, "empty_configurations": 5, "one_county_degenerate": 5,
            "empty_skips": 9995, "nonempty_draws": 29985,
            "scope": "Conditional H/D degeneracy does not zero the singleton price position, index or attainment."}

def hist_arrays(parts, primary):
    all_counts = []
    spans = []
    for b in parts:
        m = b["metadata"]
        if m["benchmark"] != "B0" or m["L"] != 6 or tuple(m["cohort_order"]) != COHORTS:
            raise ValueError("Figure1 input does not match B0/L6 three cohorts")
        if m["core_sha256"] != EXPECTED_CORE_SHA:
            raise ValueError("T1 implementation identity mismatch")
        raw = base64.b64decode(b["counts_u16_le_base64"], validate=True)
        if sha(raw) != m["counts_sha256"]:
            raise ValueError("Replicate count packet SHA mismatch")
        fields = ("condition_count", "observed_count", "reference_count", "observed_any_count",
                  "reference_any_count", "fixed_reference_count", "fixed_reference_any_count")
        if tuple(m["count_fields"]) != fields:
            raise ValueError("Count schema changed")
        counts = np.frombuffer(raw, dtype="<u2").reshape(m["rows"], 7)
        if np.any(counts == 65535) or b["invalid"]:
            raise ValueError("Unexpected invalid B0 histogram repetition")
        # Signed conversion BEFORE subtracting prevents uint16 wrap of negative D.
        all_counts.append(counts.astype(np.int64).reshape(-1, 3, 7))
        spans.extend(range(m["rep_start"], m["rep_end"] + 1))
    if spans != list(range(1, 2000)):
        raise ValueError("Exactly1999 original rep IDs in order required")
    counts = np.concatenate(all_counts, axis=0)
    out = {}
    for j, c in enumerate(COHORTS):
        r = primary[("B0", c)]
        x = counts[:, j, :]
        fixed = x[:, 5] / (r["counties"] * r["condition_count"])
        paired = (x[:, 1] - x[:, 2]) / (r["counties"] * x[:, 0])
        if not np.isclose(fixed.mean(), r["fixed_reference_mean"], rtol=0, atol=1e-12):
            raise ValueError("Figure1 fixed mean changed")
        if not np.isclose(paired.mean(), r["paired_D_mean"], rtol=0, atol=1e-12):
            raise ValueError("Figure1 paired mean changed")
        out[c] = (fixed, paired)
    return out

def validate_panels(panels):
    dates = None
    for p in panels:
        rows = p["rows"]
        d = [r["date"] for r in rows]
        if len(rows) != 315 or len(set(d)) != 315 or d != sorted(d):
            raise ValueError("Plot must preserve315 planned slots")
        if dates is not None and d != dates:
            raise ValueError("Panel calendars differ")
        dates = d
        if p["anchor_dates"] != ["2018-01-05", "2018-01-15", "2018-01-25"]:
            raise ValueError("January 2018 normalization anchor changed")
        for i, r in enumerate(rows):
            if r["national_line_connect_previous"]:
                if i == 0 or r["national_log_normalized"] is None or rows[i-1]["national_log_normalized"] is None:
                    raise ValueError("National line connects an unobserved slot")
    jp = panels[0]["rows"]
    for a, z, expected in (("2022-04-15", "2024-11-15", 94),
                            ("2024-12-05", "2026-02-15", 44)):
        selected = [r for r in jp if a <= r["date"] <= z]
        valid = [r for r in selected if r["own_price_original"] is not None
                 and float(r["own_price_original"]) == 1.5]
        if len(valid) != expected:
            raise ValueError("Jianping numerical persistence span changed")
    gap = next(r for r in jp if r["date"] == "2024-11-25")
    after = next(r for r in jp if r["date"] == "2024-12-05")
    if gap["own_log_normalized"] is not None or after["own_line_connect_previous"]:
        raise ValueError("Jianping missing slot must interrupt line")

def panel_line(ax, rows, field, connect, color, label, ls="-", lw=1.5):
    # Draw separate segments. Never connect across unavailable planned slots.
    segments, current = [], []
    for i, r in enumerate(rows):
        val = r[field]
        if val is None or not np.isfinite(val):
            if current:
                segments.append(current)
            current = []
            continue
        joins = i > 0 and connect(i, r)
        if current and not joins:
            segments.append(current)
            current = []
        current.append((datetime.fromisoformat(r["date"]), val))
    if current:
        segments.append(current)
    for j, segment in enumerate(segments):
        xs, ys = zip(*segment)
        if len(segment) == 1:
            ax.plot(xs, ys, marker=".", ms=2.5, color=color,
                    label=label if j == 0 else "_nolegend_")
        else:
            ax.plot(xs, ys, color=color, ls=ls, lw=lw,
                    label=label if j == 0 else "_nolegend_")

def style_axis(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#dddddd", linewidth=0.5, alpha=0.6)
    ax.tick_params(labelsize=9)

def save_figure(fig, name, output_dir, dpi):
    path = output_dir / name
    fig.savefig(path.with_suffix(".png"), dpi=dpi, bbox_inches="tight", pad_inches=0.08)
    fig.savefig(path.with_suffix(".tiff"), dpi=dpi, bbox_inches="tight", pad_inches=0.08,
                pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    # Lossless raster roundtrip from the verified TIFF, atomic PNG replacement.
    # Verify the lossless raster roundtrip before embedding.
    with Image.open(path.with_suffix(".tiff")) as raster:
        raster.load()
        png_temp = path.with_suffix(".png.tmp")
        raster.save(png_temp, format="PNG", dpi=(dpi, dpi))
        png_temp.replace(path.with_suffix(".png"))
    records = []
    for ext in (".png", ".tiff", ".pdf"):
        f = path.with_suffix(ext)
        entry = {"filename": f.name, "sha256": sha(f.read_bytes()), "bytes": f.stat().st_size}
        if ext in (".png", ".tiff"):
            with Image.open(f) as im:
                im.load()  # Verify full raster bytes, not only header metadata.
                stored_dpi = im.info.get("dpi")
                if not stored_dpi or min(stored_dpi) < 299:
                    raise ValueError("Raster metadata below300dpi")
                entry.update(pixels=list(im.size), stored_dpi=[float(x) for x in stored_dpi])
        records.append(entry)
    return records
