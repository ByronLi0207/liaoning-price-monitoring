#!/usr/bin/env python3
"""Project entry point: inspect, validate, prepare and run offline analysis."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "MANIFEST_SHA256.json"
_HASH = re.compile(r"[0-9a-fA-F]{64}\Z")
_CHUNK = 1024 * 1024
_MAX_MEMBER_BYTES = 512 * 1024 * 1024
_MAX_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024
_MAX_MANIFEST_BYTES = 16 * 1024 * 1024


class ProjectError(Exception):
    """A package or project does not meet the documented integrity rules."""


def _json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProjectError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def _relative_path(value):
    if not isinstance(value, str) or not value:
        raise ProjectError("A file path must be a nonempty string")
    if "\\" in value or any(ord(character) < 32 for character in value) or ":" in value:
        raise ProjectError("Unsafe file path: " + value)
    parts = value.split("/")
    if any(part in ("", ".", "..") or part.casefold() == ".git" for part in parts):
        raise ProjectError("Unsafe file path: " + value)
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ProjectError("Unsafe file path: " + value)
    return value


def _manifest_records(raw):
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_pairs)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ProjectError("The package manifest is not valid UTF-8 JSON") from error
    if not isinstance(document, dict) or not isinstance(document.get("files"), list):
        raise ProjectError("The manifest must contain a files array")
    records = {}
    portable_names = set()
    for entry in document["files"]:
        if not isinstance(entry, dict):
            raise ProjectError("A manifest entry must be an object")
        name = _relative_path(entry.get("path"))
        portable_name = unicodedata.normalize("NFC", name).casefold()
        if portable_name == MANIFEST.casefold() or portable_name in portable_names:
            raise ProjectError("Duplicate or self-referencing manifest path: " + name)
        portable_names.add(portable_name)
        size, digest = entry.get("bytes"), entry.get("sha256")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ProjectError("Invalid byte count for " + name)
        if not isinstance(digest, str) or not _HASH.fullmatch(digest):
            raise ProjectError("Invalid SHA-256 for " + name)
        records[name] = {"bytes": size, "sha256": digest.lower()}
    if not records:
        raise ProjectError("The manifest has no files")
    # A file cannot also be the parent directory of another file.
    for name in records:
        for parent in PurePosixPath(name).parents:
            if unicodedata.normalize("NFC", parent.as_posix()).casefold() in portable_names:
                raise ProjectError("File/directory conflict in manifest: " + name)
    return records


def _root(root):
    root = Path(root).absolute()
    if root.is_symlink():
        raise ProjectError("The project root must not be a symbolic link")
    return root.resolve()


def _target(root, name):
    name = _relative_path(name)
    target = root.joinpath(*PurePosixPath(name).parts)
    cursor = root
    if cursor.is_symlink():
        raise ProjectError("The project root must not be a symbolic link")
    for component in PurePosixPath(name).parts:
        cursor = cursor / component
        if cursor.is_symlink():
            raise ProjectError("Symbolic links are not accepted: " + name)
    if not target.resolve().is_relative_to(root):
        raise ProjectError("The file escapes the project root: " + name)
    return target


def _identity(stream):
    digest, size = hashlib.sha256(), 0
    while True:
        block = stream.read(_CHUNK)
        if not block:
            return size, digest.hexdigest()
        size += len(block)
        digest.update(block)


def _check_file(target, name, expected):
    if not target.is_file():
        raise ProjectError("Missing or non-file project item: " + name)
    with target.open("rb") as source:
        size, digest = _identity(source)
    if size != expected["bytes"] or digest != expected["sha256"]:
        raise ProjectError("File identity mismatch: " + name)


def verify(root=ROOT):
    """Validate every recorded payload without examining generated directories."""
    root = _root(root)
    manifest_path = _target(root, MANIFEST)
    if not manifest_path.is_file():
        raise ProjectError("The project manifest is missing. Prepare the release archive first.")
    records = _manifest_records(manifest_path.read_bytes())
    total = 0
    for name, expected in records.items():
        _check_file(_target(root, name), name, expected)
        total += expected["bytes"]
    return {"status": "PASS", "files": len(records), "bytes": total}


def _archive_inventory(archive):
    members = {}
    portable_names = set()
    expanded_bytes = 0
    for member in archive.infolist():
        name = _relative_path(member.filename.rstrip("/") if member.is_dir() else member.filename)
        portable_name = unicodedata.normalize("NFC", name).casefold()
        if portable_name in portable_names:
            raise ProjectError("Duplicate archive member: " + name)
        portable_names.add(portable_name)
        expanded_bytes += member.file_size
        if member.file_size > _MAX_MEMBER_BYTES or expanded_bytes > _MAX_ARCHIVE_BYTES:
            raise ProjectError("Archive exceeds the supported extraction size")
        mode = member.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ProjectError("Non-regular archive member: " + name)
        if member.flag_bits & 1:
            raise ProjectError("Encrypted archive member: " + name)
        members[name] = member
    return members


def prepare(root, archive_path):
    """Validate an entire archive before adding only missing project files."""
    root = _root(root)
    archive_path = Path(archive_path)
    if not archive_path.is_file():
        raise ProjectError("The release archive was not found: " + str(archive_path))
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = _archive_inventory(archive)
            manifest_names = [name for name, member in members.items()
                              if not member.is_dir() and
                              (name == MANIFEST or (len(PurePosixPath(name).parts) == 2
                                                    and name.endswith("/" + MANIFEST)))]
            if len(manifest_names) != 1:
                raise ProjectError("The archive must have one project-root manifest")
            manifest_name = manifest_names[0]
            prefix = manifest_name[:-len(MANIFEST)]
            if members[manifest_name].file_size > _MAX_MANIFEST_BYTES:
                raise ProjectError("The manifest exceeds the supported JSON size")
            raw_manifest = archive.read(members[manifest_name])
            records = _manifest_records(raw_manifest)
            expected_names = {prefix + name for name in records} | {manifest_name}
            actual_names = {name for name, member in members.items() if not member.is_dir()}
            if actual_names != expected_names:
                raise ProjectError("Archive contents do not match the package manifest")
            for name, member in members.items():
                if prefix and name != prefix.rstrip("/") and not name.startswith(prefix):
                    raise ProjectError("Archive directory lies outside the project root: " + name)
                if member.is_dir():
                    relative = name[len(prefix):] if name.startswith(prefix) else ""
                    if relative:
                        _target(root, relative)
            # Read every member to check CRC, then validate every recorded identity.
            bad_crc = archive.testzip()
            if bad_crc is not None:
                raise ProjectError("Archive CRC failure: " + bad_crc)
            for name, expected in records.items():
                with archive.open(members[prefix + name]) as source:
                    size, digest = _identity(source)
                if size != expected["bytes"] or digest != expected["sha256"]:
                    raise ProjectError("Archive file identity mismatch: " + name)
            all_expected = dict(records)
            all_expected[MANIFEST] = {"bytes": len(raw_manifest),
                                      "sha256": hashlib.sha256(raw_manifest).hexdigest()}
            missing = []
            for name, expected in all_expected.items():
                target = _target(root, name)
                for parent in target.parents:
                    if parent == root.parent:
                        break
                    if parent.exists() and not parent.is_dir():
                        raise ProjectError("Target parent is not a directory: " + name)
                if target.exists():
                    _check_file(target, name, expected)
                else:
                    missing.append(name)
            # No project write has occurred before all validation above succeeds.
            if missing:
                root.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix=".prepare-", dir=root) as temporary:
                    staging = Path(temporary)
                    for name in missing:
                        destination = staging.joinpath(*PurePosixPath(name).parts)
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(members[prefix + name]) as source, destination.open("wb") as target:
                            shutil.copyfileobj(source, target, length=_CHUNK)
                    for name in missing:
                        destination = _target(root, name)
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        # Exclusive creation ensures an intervening edit is not overwritten.
                        with destination.open("xb") as target, staging.joinpath(*PurePosixPath(name).parts).open("rb") as source:
                            shutil.copyfileobj(source, target, length=_CHUNK)
                        os.chmod(destination, 0o644)
            return {"status": "PASS", "files_verified": len(records),
                    "files_added": len(missing), "existing_files_unchanged": len(all_expected) - len(missing)}
    except (zipfile.BadZipFile, RuntimeError) as error:
        raise ProjectError("The release archive cannot be read or its CRC is invalid") from error


def info(root=ROOT):
    root = _root(root)
    panel = _target(root, "inputs/normalized_prices.csv")
    coverage = {"prepared": panel.is_file(), "analysis_counties": 12}
    if panel.is_file():
        with panel.open(encoding="utf-8-sig", newline="") as source:
            rows = list(csv.DictReader(source))
        dates = sorted({row["date"] for row in rows})
        counties = {row["region_id"] for row in rows}
        products = sorted({row["product_name"] for row in rows})
        coverage.update(records=len(rows), archived_regions=len(counties), monitoring_dates=len(dates),
                        start=dates[0] if dates else None, end=dates[-1] if dates else None,
                        products=products)
    return {"project": "AgriPrice Monitor", "purpose": "County quotation screening, benchmark comparison and alert analysis",
            "root": str(root), "coverage": coverage,
            "locations": {"data": "inputs/", "analysis": "code/", "results": "results/",
                          "figures": "figures/", "reports": "reports/", "documentation": "docs/"}}


def run_analysis(command, root=ROOT):
    root = _root(root)
    verify(root)
    script = {"reproduce": "code/reproduce_all.py", "export": "code/export_native.py"}[command]
    return subprocess.call([sys.executable, str(_target(root, script))], cwd=root)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect and run AgriPrice Monitor")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("info", help="Show project purpose and available data coverage")
    commands.add_parser("verify", help="Check all package files against the SHA-256 manifest")
    preparation = commands.add_parser("prepare", help="Validate and add missing files from a complete release archive")
    preparation.add_argument("--archive", required=True, type=Path)
    commands.add_parser("reproduce", help="Run the offline analysis pipeline")
    commands.add_parser("export", help="Export regenerated reports to PDF and page images")
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "info":
            result = info()
        elif arguments.command == "verify":
            result = verify()
        elif arguments.command == "prepare":
            result = prepare(ROOT, arguments.archive)
        else:
            return run_analysis(arguments.command)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ProjectError, OSError, KeyError) as error:
        print("Project check failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
