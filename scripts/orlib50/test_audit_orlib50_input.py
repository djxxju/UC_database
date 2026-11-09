"""Inject faults in temporary copies and check that semantic rules reject them."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_orlib50_input as audit_input


class InputFaults(unittest.TestCase):
    def check_mutation(self, mutate, expected_error):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp)
            for name in ("input.json", "provenance.json", "LICENSE.txt"):
                shutil.copyfile(audit_input.CASE / name, case / name)
            source = json.loads((case / "input.json").read_bytes())
            mutate(source)
            raw = json.dumps(source).encode("utf-8")
            (case / "input.json").write_bytes(raw)

            # Refresh the fixture checksum so the semantic rule can be reached.
            manifest_path = case / "provenance.json"
            provenance = json.loads(manifest_path.read_bytes())
            provenance.update(input_sha256=audit_input.sha(raw), input_bytes=len(raw))
            manifest_path.write_text(json.dumps(provenance), encoding="utf-8")
            with patch.object(audit_input, "CASE", case):
                with self.assertRaisesRegex(ValueError, f"^{expected_error}$"):
                    audit_input.audit(write=True)

    def test_shortened_load_series(self):
        self.check_mutation(
            lambda data: data["Buses"]["b1"]["Load (MW)"].pop(),
            "time_series: hourly_array_lengths_match_horizon",
        )

    def test_nonzero_reserve(self):
        def mutate(data):
            data["Reserves"]["r1"]["Amount (MW)"][0] = 1

        self.check_mutation(mutate, "time_series: zero_spinning_reserve_source_values")

    def test_foreign_bus(self):
        def mutate(data):
            next(iter(data["Generators"].values()))["Bus"] = "unlisted_bus"

        self.check_mutation(mutate, "relationships: generator_bus_and_reserve_foreign_keys")

    def test_repeated_cost_point(self):
        def mutate(data):
            points = next(iter(data["Generators"].values()))["Production cost curve (MW)"]
            points[1] = points[0]

        self.check_mutation(mutate, "parameters: pwl_shapes_and_increasing_output")

    def test_offline_unit_with_output(self):
        def mutate(data):
            unit = next(unit for unit in data["Generators"].values() if unit["Initial status (h)"] < 0)
            unit["Initial power (MW)"] = 1

        self.check_mutation(mutate, "parameters: initial_on_off_output_consistency")


if __name__ == "__main__":
    unittest.main(verbosity=2)
