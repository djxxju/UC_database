"""Audit the fixed OR-LIB 20_0_1_w input and verify its lossless CSV views."""

import argparse
import csv
import gzip
import hashlib
import io
import json
import platform
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

from jsonschema import Draft202012Validator


HERE = Path(__file__).resolve().parent
CASE = HERE.parents[1] / "cases" / "orlib_20_0_1_w"
GEN_FIELDS = {
    "bus_id": "Bus",
    "initial_status_h": "Initial status (h)",
    "initial_power_mw": "Initial power (MW)",
    "minimum_uptime_h": "Minimum uptime (h)",
    "minimum_downtime_h": "Minimum downtime (h)",
    "ramp_up_limit_mw": "Ramp up limit (MW)",
    "ramp_down_limit_mw": "Ramp down limit (MW)",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique_keys(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ValueError(f"duplicate JSON key: {key}")
        fields[key] = value
    return fields


def reject_constant(token):
    raise ValueError(f"non-finite JSON token: {token}")


def csv_bytes(headers, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def verify_or_create(path, expected, write):
    if write and not path.exists():
        with path.open("xb") as stream:
            stream.write(expected)
    if path.read_bytes() != expected:
        raise ValueError(f"unexpected file content: {path}")


def audit(source_gzip=None, write=False):
    checks = []

    def check(rule, condition, layer):
        if not condition:
            raise ValueError(f"{layer}: {rule}")
        checks.append({"rule": rule, "layer": layer, "status": "passed"})

    provenance = json.loads((CASE / "provenance.json").read_bytes())
    raw = (CASE / "input.json").read_bytes()
    if source_gzip is not None:
        compressed = source_gzip.read_bytes()
        check("gzip_hash_matches_collection_records",
              sha(compressed) == provenance["source_gzip_sha256"], "identity")
        check("input_matches_decompressed_gzip_byte_for_byte",
              gzip.decompress(compressed) == raw, "identity")
    check("input_sha256_matches_manifest", sha(raw) == provenance["input_sha256"], "identity")
    data = json.loads(raw, parse_float=Decimal, object_pairs_hook=unique_keys, parse_constant=reject_constant)
    check("strict_json_parse_unique_keys_and_finite_number_tokens", True, "structure")
    schema = json.loads((HERE / "input.schema.json").read_bytes())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(raw))
    check("structural_schema_draft_2020_12", True, "structure")
    license_bytes = data["LICENSE"].encode("utf-8")
    check("embedded_license_hash_and_source_references_match_archive",
          sha(license_bytes) == provenance["embedded_license_sha256"]
          and data["SOURCE"] == provenance["embedded_source_text"], "identity")
    verify_or_create(CASE / "LICENSE.txt", license_bytes, write)
    check("license_copy_byte_for_byte", True, "identity")

    generators = data["Generators"]
    buses = data["Buses"]
    reserves = data["Reserves"]
    horizon = data["Parameters"]["Time (h)"]
    check("fixed_profile_20_generators_1_bus_1_reserve_24_hours",
          horizon == 24 and len(generators) == 20 and set(buses) == {"b1"}
          and set(reserves) == {"r1"} and reserves["r1"]["Type"] == "Spinning", "structure")
    generator_keys = set(GEN_FIELDS.values()) | {
        "Production cost curve (MW)", "Production cost curve ($)",
        "Startup costs ($)", "Startup delays (h)", "Reserve eligibility",
    }
    check("flat_native_fields_with_no_unmapped_generator_entries",
          all(set(g) == generator_keys for g in generators.values()), "structure")
    check("generator_bus_and_reserve_foreign_keys",
          all(g["Bus"] in buses and len(set(g["Reserve eligibility"])) == len(g["Reserve eligibility"])
              and all(r in reserves for r in g["Reserve eligibility"])
              for g in generators.values()), "relationships")
    loads = buses["b1"]["Load (MW)"]
    reserve = reserves["r1"]["Amount (MW)"]
    check("hourly_array_lengths_match_horizon", len(loads) == len(reserve) == horizon, "time_series")
    check("zero_spinning_reserve_source_values", all(value == 0 for value in reserve), "time_series")
    check("pwl_shapes_and_increasing_output",
          all(len(x) == len(y) and all(a < b for a, b in zip(x, x[1:]))
              for g in generators.values()
              for x, y in [(g["Production cost curve (MW)"], g["Production cost curve ($)"])]),
          "parameters")
    slopes = [
        [(d - c) / (b - a) for a, b, c, d in zip(x, x[1:], y, y[1:])]
        for g in generators.values()
        for x, y in [(g["Production cost curve (MW)"], g["Production cost curve ($)"])]
    ]
    check("pwl_convexity_tolerance_1e_9",
          all(b >= a - Decimal("1e-9") for s in slopes for a, b in zip(s, s[1:])), "parameters")
    check("single_startup_tier_and_first_delay_equals_minimum_down",
          all(len(g["Startup costs ($)"]) == len(g["Startup delays (h)"]) == 1
              and g["Startup delays (h)"][0] == g["Minimum downtime (h)"]
              for g in generators.values()), "parameters")
    check("initial_on_off_output_consistency",
          all((x[0] <= p <= x[-1]) if g["Initial status (h)"] > 0 else p == 0
              for g in generators.values()
              for x, p in [(g["Production cost curve (MW)"], g["Initial power (MW)"])]),
          "parameters")
    capacity = sum(g["Production cost curve (MW)"][-1] for g in generators.values())
    check("aggregate_capacity_covers_demand_plus_reserve",
          all(demand + requirement <= capacity for demand, requirement in zip(loads, reserve)),
          "necessary_condition")

    unit_rows = [
        (unit, *(g[field] for field in GEN_FIELDS.values()), g["Production cost curve (MW)"][0],
         g["Production cost curve (MW)"][-1], "|".join(g["Reserve eligibility"]))
        for unit, g in generators.items()
    ]
    cost_rows = [
        (unit, index, mw, cost)
        for unit, g in generators.items()
        for index, (mw, cost) in enumerate(zip(g["Production cost curve (MW)"],
                                              g["Production cost curve ($)"]), 1)
    ]
    startup_rows = [
        (unit, index, delay, cost)
        for unit, g in generators.items()
        for index, (delay, cost) in enumerate(zip(g["Startup delays (h)"], g["Startup costs ($)"]), 1)
    ]
    hourly_rows = [
        (hour, "b1", demand, "r1", requirement)
        for hour, (demand, requirement) in enumerate(zip(loads, reserve), 1)
    ]
    views = {
        "generators.csv": (("generator_id", *GEN_FIELDS, "pmin_mw", "pmax_mw", "reserve_ids"), unit_rows),
        "cost_points.csv": (("generator_id", "point_index", "output_mw", "production_cost_dollars"), cost_rows),
        "startup_tiers.csv": (("generator_id", "tier_index", "prior_offline_delay_h", "startup_cost_dollars"),
                              startup_rows),
        "hourly.csv": (("hour", "bus_id", "load_mw", "reserve_id", "reserve_requirement_mw"), hourly_rows),
    }
    for filename, (headers, rows) in views.items():
        verify_or_create(CASE / filename, csv_bytes(headers, rows), write)
        check(f"{filename}_matches_regenerated_source_mapping", True, "derived_view")

    return {
        "case_id": "orlib_20_0_1_w",
        "input_sha256": sha(raw),
        "python_version": platform.python_version(),
        "jsonschema_version": version("jsonschema"),
        "schema_sha256": sha((HERE / "input.schema.json").read_bytes()),
        "audit_script_sha256": sha(Path(__file__).read_bytes()),
        "source_gzip_rechecked": source_gzip is not None,
        "checks": checks,
        "passed_count": len(checks),
        "generator_count": len(generators),
        "cost_point_count": len(cost_rows),
        "startup_tier_count": len(startup_rows),
        "period_count": horizon,
        "initial_online_count": sum(g["Initial status (h)"] > 0 for g in generators.values()),
        "aggregate_capacity_mw": str(capacity),
        "peak_demand_mw": str(max(loads)),
        "peak_hour": loads.index(max(loads)) + 1,
        "total_load_mwh": str(sum(loads)),
        "boundary": "Input audit and necessary conditions only. Solve and solution verification are separate.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-gzip", type=Path)
    parser.add_argument("--write", action="store_true", help="create missing views, without overwriting")
    args = parser.parse_args()
    print(json.dumps(audit(args.source_gzip, args.write), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
