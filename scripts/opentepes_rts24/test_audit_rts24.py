"""Exercise full-horizon semantic gates with isolated, in-memory input faults."""

import argparse
import unittest

from audit_rts24 import add_source_arguments, check_static, check_timeseries, read_package


class InputFaults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables, _ = read_package(cls.source_dir, cls.license_file)
        cls.static = check_static(cls.tables)

    def replace(self, table, row, field, value):
        fields, original_rows = self.tables[table]
        rows = original_rows.copy()
        rows[row] = rows[row].copy()
        rows[row][fields.index(field)] = value
        return {**self.tables, table: (fields, rows)}

    def check_faulty_series(self, tables, rule):
        with self.assertRaisesRegex(ValueError, rule):
            check_timeseries(tables, *self.static[:-1])

    def test_unknown_network_endpoint(self):
        tables = self.replace("Data_Network", 0, "InitialNode", "UNKNOWN")
        with self.assertRaisesRegex(ValueError, "branch references"):
            check_static(tables)

    def test_minimum_power_above_maximum(self):
        tables = self.replace("Data_Generation", 0, "MinimumPower", "21")
        with self.assertRaisesRegex(ValueError, "generator capacity"):
            check_static(tables)

    def test_last_hour_load_key_mismatch(self):
        tables = self.replace("Data_Demand", -1, "LoadLevel", "12-30 22:00:00+01:00")
        self.check_faulty_series(tables, "full ordered time keys")

    def test_negative_last_hour_load(self):
        tables = self.replace("Data_Demand", -1, "N_101", "-1")
        self.check_faulty_series(tables, "nonnegative nodal demand")

    def test_inflow_on_nonstorage_generator(self):
        tables = self.replace("Data_EnergyInflows", -1, "Gas_C1", "1")
        self.check_faulty_series(tables, "storage inflow scope or sign")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    add_source_arguments(parser)
    args, unittest_args = parser.parse_known_args()
    InputFaults.source_dir = args.source_dir
    InputFaults.license_file = args.license_file
    unittest.main(argv=[__file__, *unittest_args], verbosity=2)
