"""Regress slim-package validation and optional exports without changing its inputs."""

import contextlib
import gzip
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import audit_input


class OptionalViews(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.case = Path(self.temporary.name) / "case"
        shutil.copytree(audit_input.CASE, self.case)

    @contextlib.contextmanager
    def copied_case(self):
        original = audit_input.CASE
        audit_input.CASE = self.case
        try:
            yield
        finally:
            audit_input.CASE = original

    def test_missing_views_are_optional_and_write_recreates_them(self):
        with self.copied_case():
            before = (self.case / "input.json").read_bytes()
            self.assertEqual(audit_input.audit()["optional_csv_views_checked"], [])
            exported = audit_input.audit(write=True)
            self.assertEqual(len(exported["optional_csv_views_checked"]), 4)
            self.assertEqual(len(audit_input.audit()["optional_csv_views_checked"]), 4)
            self.assertEqual(before, (self.case / "input.json").read_bytes())

    def test_existing_wrong_view_is_rejected(self):
        (self.case / "hourly.csv").write_text("wrong data\n", encoding="utf-8")
        with self.copied_case(), self.assertRaisesRegex(ValueError, "unexpected file content"):
            audit_input.audit()

    def test_modified_values_fail_identity_check(self):
        path = self.case / "input.json"
        data = json.loads(path.read_bytes())
        data["Buses"]["b1"]["Load (MW)"][0] += 1
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.copied_case(), self.assertRaisesRegex(ValueError, "input_sha256_matches_manifest"):
            audit_input.audit()

    def test_valid_reformatting_requires_matching_provenance(self):
        path = self.case / "input.json"
        data = json.loads(path.read_bytes())
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        provenance_path = self.case / "provenance.json"
        provenance = json.loads(provenance_path.read_bytes())
        provenance["input_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
        with self.copied_case():
            self.assertTrue(audit_input.audit()["passed_count"] > 0)

    def test_source_comparison_detects_value_change_with_updated_file_hash(self):
        path = self.case / "input.json"
        source = path.read_bytes()
        archive = self.case / "test.json.gz"
        archive.write_bytes(gzip.compress(source))
        data = json.loads(source)
        data["Buses"]["b1"]["Load (MW)"][0] += 1
        path.write_text(json.dumps(data), encoding="utf-8")
        provenance_path = self.case / "provenance.json"
        provenance = json.loads(provenance_path.read_bytes())
        provenance.update(
            source_gzip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            source_unpacked_sha256=hashlib.sha256(source).hexdigest(),
            input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
        with self.copied_case(), self.assertRaisesRegex(ValueError, "input_values_match_archived_json"):
            audit_input.audit(archive)


if __name__ == "__main__":
    unittest.main(verbosity=2)
