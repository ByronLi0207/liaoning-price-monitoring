"""Integrity and preparation tests use small isolated fixtures only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile

_ENTRY = Path(__file__).resolve().parents[1] / "scripts" / "project.py"
_SPEC = importlib.util.spec_from_file_location("project_entry", _ENTRY)
project = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(project)


def manifest(payload):
    return json.dumps({"files": [
        {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in payload.items()
    ]}).encode("utf-8")


def archive(path, payload, extra=None, declared=None):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as target:
        target.writestr("agri-price-monitor/MANIFEST_SHA256.json", declared or manifest(payload))
        for name, data in payload.items():
            target.writestr("agri-price-monitor/" + name, data)
        for name, data in (extra or []):
            target.writestr(name, data)
    return path


class ProjectPackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="project-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "project"
        self.payload = {"code/core.py": b"print('analysis entry')\n",
                        "inputs/data.csv": b"date,value\n2020-01-01,2\n"}

    def test_prepare_adds_missing_files_without_changing_matching_source(self):
        self.root.joinpath("code").mkdir(parents=True)
        existing = self.root / "code/core.py"
        existing.write_bytes(self.payload["code/core.py"])
        timestamp = existing.stat().st_mtime_ns
        result = project.prepare(self.root, archive(self.base / "valid.zip", self.payload))
        self.assertEqual(result["files_added"], 2)
        self.assertEqual(existing.stat().st_mtime_ns, timestamp)
        self.assertEqual(project.verify(self.root)["files"], 2)
        second = project.prepare(self.root, self.base / "valid.zip")
        self.assertEqual(second["files_added"], 0)

    def test_hash_corruption_is_rejected_before_root_creation(self):
        broken = dict(self.payload)
        broken["inputs/data.csv"] = b"modified data"
        package = archive(self.base / "corrupt.zip", broken, declared=manifest(self.payload))
        with self.assertRaisesRegex(project.ProjectError, "identity mismatch"):
            project.prepare(self.root, package)
        self.assertFalse(self.root.exists())

    def test_crc_corruption_is_rejected_before_root_creation(self):
        package = self.base / "crc.zip"
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_STORED) as target:
            target.writestr("agri-price-monitor/MANIFEST_SHA256.json", manifest(self.payload))
            for name, data in self.payload.items():
                target.writestr("agri-price-monitor/" + name, data)
        with zipfile.ZipFile(package) as source:
            member = source.getinfo("agri-price-monitor/inputs/data.csv")
            offset = member.header_offset + 30 + len(member.filename.encode()) + len(member.extra)
        damaged = bytearray(package.read_bytes())
        damaged[offset] ^= 1
        package.write_bytes(damaged)
        with self.assertRaisesRegex(project.ProjectError, "CRC"):
            project.prepare(self.root, package)
        self.assertFalse(self.root.exists())

    def test_duplicate_member_is_rejected_before_root_creation(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            package = archive(self.base / "duplicate.zip", self.payload,
                              [("agri-price-monitor/code/core.py", self.payload["code/core.py"])])
        with self.assertRaisesRegex(project.ProjectError, "Duplicate"):
            project.prepare(self.root, package)
        self.assertFalse(self.root.exists())

    def test_case_collision_is_rejected(self):
        payload = {"code/core.py": b"one", "code/CORE.py": b"two"}
        with self.assertRaisesRegex(project.ProjectError, "Duplicate"):
            project.prepare(self.root, archive(self.base / "case.zip", payload))
        self.assertFalse(self.root.exists())

    def test_file_directory_conflict_is_rejected(self):
        payload = {"code": b"file", "CODE/core.py": b"child"}
        with self.assertRaisesRegex(project.ProjectError, "File/directory conflict"):
            project.prepare(self.root, archive(self.base / "file-dir.zip", payload))
        self.assertFalse(self.root.exists())

    def test_path_traversal_and_git_paths_are_rejected(self):
        for index, name in enumerate(("../escaped.txt", "agri-price-monitor/../escaped.txt",
                                      "/absolute.txt", "agri-price-monitor/.git/config",
                                      "agri-price-monitor/code\\escape.txt")):
            with self.subTest(name=name):
                package = archive(self.base / ("unsafe%d.zip" % index), self.payload, [(name, b"bad")])
                with self.assertRaisesRegex(project.ProjectError, "Unsafe"):
                    project.prepare(self.root, package)
                self.assertFalse(self.root.exists())
                self.assertFalse(self.base.joinpath("escaped.txt").exists())

    def test_changed_existing_source_rejects_all_writes(self):
        self.root.joinpath("code").mkdir(parents=True)
        existing = self.root / "code/core.py"
        existing.write_bytes(b"user changes\n")
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        with self.assertRaisesRegex(project.ProjectError, "identity mismatch"):
            project.prepare(self.root, archive(self.base / "valid.zip", self.payload))
        self.assertEqual(existing.read_bytes(), b"user changes\n")
        after = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        self.assertEqual(before, after)

    def test_existing_symlink_cannot_escape_root(self):
        self.root.mkdir()
        outside = self.base / "outside"
        outside.mkdir()
        self.root.joinpath("inputs").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(project.ProjectError, "Symbolic links"):
            project.prepare(self.root, archive(self.base / "valid.zip", self.payload))
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(self.root.joinpath("code").exists())

    def test_archive_symlink_is_rejected(self):
        package = archive(self.base / "link.zip", self.payload)
        with zipfile.ZipFile(package, "a") as target:
            link = zipfile.ZipInfo("agri-price-monitor/link")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            target.writestr(link, "../outside")
        with self.assertRaisesRegex(project.ProjectError, "Non-regular"):
            project.prepare(self.root, package)
        self.assertFalse(self.root.exists())

    def test_unlisted_member_is_rejected(self):
        package = archive(self.base / "extra.zip", self.payload,
                          [("agri-price-monitor/extra.txt", b"not recorded")])
        with self.assertRaisesRegex(project.ProjectError, "do not match"):
            project.prepare(self.root, package)
        self.assertFalse(self.root.exists())

    def test_duplicate_manifest_paths_are_rejected(self):
        document = json.loads(manifest(self.payload))
        document["files"].append(document["files"][0])
        package = archive(self.base / "bad-manifest.zip", self.payload,
                          declared=json.dumps(document).encode())
        with self.assertRaisesRegex(project.ProjectError, "Duplicate"):
            project.prepare(self.root, package)
        self.assertFalse(self.root.exists())

    def test_verifier_ignores_new_generated_outputs_and_checks_missing_input(self):
        project.prepare(self.root, archive(self.base / "valid.zip", self.payload))
        output = self.root / "reproduction"
        output.mkdir()
        output.joinpath("run.log").write_text("generated\n")
        self.assertEqual(project.verify(self.root)["status"], "PASS")
        self.root.joinpath("inputs/data.csv").unlink()
        with self.assertRaisesRegex(project.ProjectError, "Missing"):
            project.verify(self.root)

    def test_archive_size_limit_is_enforced_before_writing(self):
        original = project._MAX_MEMBER_BYTES
        try:
            project._MAX_MEMBER_BYTES = 8
            with self.assertRaisesRegex(project.ProjectError, "extraction size"):
                project.prepare(self.root, archive(self.base / "size.zip", self.payload))
        finally:
            project._MAX_MEMBER_BYTES = original
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
