"""Audit the fixed RTS24 input package across its complete source horizon."""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path


PROVENANCE = (Path(__file__).resolve().parents[2] / "cases"
              / "opentepes_rts24_full_inputs_v1" / "provenance.json")
KEY = ("Period", "Scenario", "LoadLevel")
TEXT_FIELDS = {
    "Generator", "Node", "Technology", "MutuallyExclusive", "StorageType", "OutflowsType",
    "EnergyType", "MustRun", "OutflowsIncompatibility", "NoOperatingReserve", "BinaryCommitment",
    "StorageInvestment", "BinaryInvestment", "BinaryRetirement", "InitialNode", "FinalNode",
    "Circuit", "LineType", "Switching", "Converter", "ReferenceNode", "Scenario", "Stage", "Area",
}


def require(condition, rule):
    if not condition:
        raise ValueError(rule)


def number(token):
    value = Decimal(token)
    require(value.is_finite(), f"non-finite number {token}")
    return value


def read_package(source_dir, license_file):
    manifest = json.loads(PROVENANCE.read_bytes())
    require(manifest["commit"] == "5c0187063874cca4bc7af8ff97b19c6c316dd7a5", "source commit")
    paths = {p.name for p in source_dir.iterdir() if p.is_file()}
    require(paths == {record["path"] for record in manifest["files"]} and len(paths) == 44,
            "source file inventory")
    tables, inventory = {}, {}
    for record in manifest["files"]:
        path = source_dir / record["path"]
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        blob = hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()
        require((len(payload), digest, blob) == (record["bytes"], record["sha256"], record["git_blob"]),
                f"source identity: {path.name}")
        fields, *rows = csv.reader(io.StringIO(payload.decode("utf-8-sig"), newline=""), strict=True)
        require(all(fields) and len(set(fields)) == len(fields)
                and all(len(row) == len(fields) for row in rows), f"CSV shape: {path.name}")
        tables[path.stem.removeprefix("oT_").removesuffix("_RTS24")] = (tuple(fields), rows)
        inventory[path.name] = {"rows": len(rows), "columns": len(fields), "sha256": digest, "git_blob": blob}
    license_digest = hashlib.sha256(license_file.read_bytes()).hexdigest()
    require(license_digest == manifest["license_sha256"], "license identity")
    return tables, {"commit": manifest["commit"], "license_sha256": license_digest, "files": inventory}


def records(tables, name, keys):
    fields, rows = tables[name]
    records_by_key = {}
    for row in rows:
        item = dict(zip(fields, row, strict=True))
        key = tuple(item[field] for field in keys)
        require(all(key) and key not in records_by_key, f"missing or duplicate key in {name}: {key}")
        records_by_key[key] = item
    return records_by_key


def members(tables, dictionary):
    fields, rows = tables[f"Dict_{dictionary}"]
    require(len(fields) == 1, f"dictionary shape: {dictionary}")
    records(tables, f"Dict_{dictionary}", fields)
    return tuple(row[0] for row in rows)


def check_static(tables):
    dicts = {name: members(tables, name) for name in (
        "Area", "Circuit", "Generation", "Line", "LoadLevel", "Node", "Period", "Region",
        "Scenario", "Stage", "Storage", "Technology", "Zone",
    )}
    for name, left, right in (
        ("NodeToZone", "Node", "Zone"), ("ZoneToArea", "Zone", "Area"), ("AreaToRegion", "Area", "Region"),
    ):
        fields, rows = tables["Dict_" + name]
        mapping = records(tables, "Dict_" + name, fields[:1])
        require(set(mapping) == {(x,) for x in dicts[left]} and all(row[1] in dicts[right] for row in rows),
                f"complete hierarchy mapping: {name}")
    for table, dictionary, key in (
        ("Data_Period", "Period", "Period"), ("Data_Stage", "Stage", "Stage"),
        ("Data_NodeLocation", "Node", "Node"), ("Data_Generation", "Generation", "Generator"),
    ):
        require(set(records(tables, table, (key,))) == {(x,) for x in dicts[dictionary]}, f"dictionary match: {table}")
    scenario_keys = {(period, scenario) for period in dicts["Period"] for scenario in dicts["Scenario"]}
    scenarios = records(tables, "Data_Scenario", ("Period", "Scenario"))
    require(set(scenarios) == scenario_keys, "period and scenario relation")
    for period in dicts["Period"]:
        require(sum(number(row["Probability"]) for key, row in scenarios.items() if key[0] == period) == 1
                and all(number(row["Probability"]) > 0 for key, row in scenarios.items() if key[0] == period),
                f"scenario probabilities: {period}")
    for table in ("Data_Period", "Data_Stage"):
        require(all(number(row[-1]) > 0 for row in tables[table][1]), f"positive weights: {table}")
    for table in ("Data_Emission", "Data_RESEnergy", "Data_ReserveMargin"):
        require(set(records(tables, table, ("Period", "Area"))) ==
                {(p, a) for p in dicts["Period"] for a in dicts["Area"]}, f"period and area relation: {table}")
    blank_columns = {}
    for name, (fields, rows) in tables.items():
        if not name.startswith("Data_") or fields[:3] == KEY:
            continue
        blank_columns[name] = dict(Counter(field for row in rows for field, token in zip(fields, row, strict=True)
                                           if not token))
        for row in rows:
            for field, token in zip(fields, row, strict=True):
                if field not in TEXT_FIELDS and token:
                    number(token)

    for table in ("Data_Option", "Data_Parameter"):
        require(len(tables[table][1]) == 1, f"singleton input: {table}")
    parameter = dict(zip(tables["Data_Parameter"][0], tables["Data_Parameter"][1][0], strict=True))
    option = dict(zip(tables["Data_Option"][0], tables["Data_Option"][1][0], strict=True))
    require(all(value in {"0", "1"} for value in option.values()), "binary option values")
    require(parameter["ReferenceNode"] in dicts["Node"] and number(parameter["SBase"]) > 0,
            "reference node and base power")
    step = int(parameter["TimeStep"])
    require(step == 2, "fixed case TimeStep")

    generation = records(tables, "Data_Generation", ("Generator",))
    branches = records(tables, "Data_Network", ("InitialNode", "FinalNode", "Circuit"))
    require((len(dicts["Node"]), len(generation), len(branches)) == (24, 33, 38), "fixed case dimensions")
    require(all(-90 <= number(row["Latitude"]) <= 90 and -180 <= number(row["Longitude"]) <= 180
                for row in records(tables, "Data_NodeLocation", ("Node",)).values()), "node coordinates")
    storages, zero_power, blank_voltage, hydro_classification = set(), [], [], []
    raw_capacity = derated_capacity = Decimal(0)
    for (name,), row in generation.items():
        require(row["Node"] in dicts["Node"] and row["Technology"] in dicts["Technology"], f"generation references: {name}")
        require(int(row["InitialPeriod"]) <= int(dicts["Period"][0]) <= int(row["FinalPeriod"]),
                f"generator active period: {name}")
        pmax = number(row["MaximumPower"])
        # Fixed-source reader defaults missing numeric inputs internally. The raw fields remain empty.
        pmin, efor = (number(row[field] or "0") for field in ("MinimumPower", "EFOR"))
        require(0 <= pmin <= pmax and 0 <= efor < 1 and 0 < number(row["Availability"]) <= 1,
                f"generator capacity or availability: {name}")
        require(number(row["MinimumReactivePower"]) <= number(row["MaximumReactivePower"]),
                f"reactive range: {name}")
        require(all(not row[field] or number(row[field]) >= 0 for field in (
            "RampUp", "RampDown", "UpTime", "DownTime", "StableTime", "MaximumCharge", "MinimumCharge"
        )), f"ramp, duration or charging sign: {name}")
        raw_capacity += pmax
        derated_capacity += pmax * (1 - efor)
        if row["Technology"] == "Coal" and number(row["ProductionFunctionHydro"] or "0") > 0:
            hydrogen = number(row["ProductionFunctionH2"] or "0")
            heat = number(row["ProductionFunctionHeat"] or "0")
            hydro_classification.append({
                "generator": name, "technology": row["Technology"],
                "raw_production_function_hydro": row["ProductionFunctionHydro"],
                "raw_production_function_h2": row["ProductionFunctionH2"],
                "raw_production_function_heat": row["ProductionFunctionHeat"],
                "enters_h_under_source_predicate": hydrogen == heat == 0,
                "enters_es_under_source_predicate": False,
                "status": "UNVERIFIED_AUTHOR_INTENT_AND_GENERATED_CONSTRAINTS",
            })
        if pmax == 0:
            zero_power.append(name)
        if row["StorageType"]:
            require(row["StorageType"] in dicts["Storage"] and row["OutflowsType"] in dicts["Storage"],
                    f"storage reference: {name}")
            lo, initial, hi = (number(row[field]) for field in ("MinimumStorage", "InitialStorage", "MaximumStorage"))
            require(0 <= lo <= initial <= hi and 0 < number(row["Efficiency"]) <= 1,
                    f"storage bounds and efficiency: {name}")
            storages.add(name)
    adjacency, pairs, fallback_reverse = defaultdict(set), Counter(), 0
    for (a, b, circuit), row in branches.items():
        require(a in dicts["Node"] and b in dicts["Node"] and a != b and circuit in dicts["Circuit"]
                and row["LineType"] in dicts["Line"], f"branch references: {(a, b, circuit)}")
        require(int(row["InitialPeriod"]) <= int(dicts["Period"][0]) <= int(row["FinalPeriod"]),
                f"branch active period: {(a, b, circuit)}")
        require(number(row["Reactance"]) > 0 and number(row["Resistance"]) >= 0 and number(row["Tap"]) > 0
                and number(row["TTC"]) > 0 and 0 < number(row["SecurityFactor"]) <= 1
                and number(row["AngMin"]) <= number(row["AngMax"]), f"branch electrical limits: {(a, b, circuit)}")
        if not row["TTCBck"] or number(row["TTCBck"]) <= 0:
            fallback_reverse += 1
        if not row["Voltage"]:
            blank_voltage.append((a, b, circuit))
        adjacency[a].add(b)
        adjacency[b].add(a)
        pairs[tuple(sorted((a, b)))] += 1
    visited = set()
    pending = {parameter["ReferenceNode"]}
    while pending:
        node = pending.pop()
        visited.add(node)
        pending.update(adjacency[node] - visited)
    require(visited == set(dicts["Node"]), "reference-node network connectivity")
    summary = {
        "dictionary_sizes": {key: len(values) for key, values in dicts.items()},
        "technology_counts": dict(Counter(row["Technology"] for row in generation.values())),
        "network_lines": len(branches), "parallel_pairs": [pair for pair, count in pairs.items() if count > 1],
        "reference_node": parameter["ReferenceNode"], "blank_voltage_lines": blank_voltage,
        "reverse_capacity_fallback_line_count": fallback_reverse,
        "storage_generators": sorted(storages), "zero_active_power_records": zero_power,
        "raw_capacity_mw": str(raw_capacity), "derated_capacity_mw": str(derated_capacity),
        "static_blank_counts_by_column": blank_columns, "option": option,
        "semantic_review_items": hydro_classification,
    }
    return dicts, scenario_keys, step, storages, derated_capacity, summary


def check_timeseries(tables, dicts, scenario_keys, step, storages, capacity):
    fields, duration = tables["Data_Duration"]
    require(fields == (*KEY, "Duration", "Stage"), "duration schema")
    time_keys = [tuple(row[:3]) for row in duration]
    require(len(time_keys) == len(set(time_keys)) == 8736 and {key[:2] for key in time_keys} == scenario_keys,
            "source horizon and unique period/scenario/time keys")
    require(tuple(key[2] for key in time_keys) == dicts["LoadLevel"]
            and all(row[3] == "1" and row[4] in dicts["Stage"] for row in duration), "duration and stage mapping")
    parsed = [datetime.fromisoformat(f"{p}-{label}") for p, _, label in time_keys]
    require(all(b - a == timedelta(hours=1) for a, b in zip(parsed, parsed[1:])), "continuous source time axis")
    require(len(time_keys) % step == 0 and len({row[4] for row in duration}) == 1, "complete source step groups")
    results, load_rows, reserve_up, inflow_rows = {}, [], [], []
    for name, (fields, rows) in sorted(tables.items()):
        if fields[:3] != KEY:
            continue
        require([tuple(row[:3]) for row in rows] == time_keys, f"full ordered time keys: {name}")
        expected = (
            ("Duration", "Stage") if name == "Data_Duration" else dicts["Node"] if name == "Data_Demand"
            else dicts["Area"] if name in {"Data_Inertia", "Data_OperatingReserveUp", "Data_OperatingReserveDown"}
            else dicts["Generation"]
        )
        require(fields[3:] == expected, f"ordered entity columns: {name}")
        counts = Counter()
        low = high = None
        for row in rows:
            values = []
            for field, token in zip(fields[3:], row[3:], strict=True):
                if field == "Stage" or not token:
                    continue
                val = number(token)
                counts[field] += 1
                values.append(val)
                low = val if low is None else min(low, val)
                high = val if high is None else max(high, val)
            if name == "Data_Demand":
                require(len(values) == len(expected) and min(values) >= 0, "explicit nonnegative nodal demand")
                load_rows.append(values)
            elif name in {"Data_OperatingReserveUp", "Data_OperatingReserveDown"}:
                require(values == [0] * len(expected), f"explicit zero reserve values: {name}")
                if name == "Data_OperatingReserveUp":
                    reserve_up.append(sum(values))
            elif name == "Data_EnergyInflows":
                require(set(field for field, token in zip(expected, row[3:], strict=True) if token) == storages
                        and all(v >= 0 for v in values), "storage inflow scope or sign")
                inflow_rows.append(values)
        numeric_cols = len(expected) - ("Stage" in expected)
        numeric_count = sum(counts.values())
        if name.startswith("Data_Variable") or name in {"Data_Inertia", "Data_EnergyOutflows"}:
            require(numeric_count == 0, f"blank optional series in fixed source: {name}")
        results[name] = {"rows": len(rows), "numeric_cells": numeric_count,
                         "raw_blank_cells": len(rows) * numeric_cols - numeric_count,
                         "minimum": str(low) if low is not None else None,
                         "maximum": str(high) if high is not None else None,
                         "populated_columns": dict(counts)}
    require(len(results) == 17, "full time-series table inventory")
    def step_means(values, label):
        effective_values = [
            tuple(sum(column) / step for column in zip(*values[i:i + step], strict=True))
            for i in range(0, len(values), step)
        ]
        raw_energy = tuple(map(sum, zip(*values, strict=True)))
        effective_energy = tuple(sum(column) * step for column in zip(*effective_values, strict=True))
        require(raw_energy == effective_energy, f"energy preservation over complete effective horizon: {label}")
        return effective_values, raw_energy

    effective, raw_energy = step_means(load_rows, "nodal demand")
    _, inflow_energy = step_means(inflow_rows, "storage inflows")
    raw_peak = max(map(sum, load_rows))
    peak_index = max(range(len(effective)), key=lambda i: sum(effective[i]))
    effective_peak = sum(effective[peak_index])
    raw_capacity_shortfalls = sum(sum(row) + reserve > capacity for row, reserve in zip(load_rows, reserve_up, strict=True))
    effective_capacity_shortfalls = sum(sum(row) > capacity for row in effective)
    return {
        "tables": results, "source_hour_count": len(time_keys), "model_period_hours": step,
        "effective_period_count": len(effective), "first_effective_label": parsed[step - 1].isoformat(),
        "last_effective_label": parsed[-1].isoformat(), "raw_peak_mw": str(raw_peak),
        "effective_peak_mw": str(effective_peak), "effective_peak_label": parsed[(peak_index + 1) * step - 1].isoformat(),
        "source_total_load_mwh": str(sum(raw_energy)),
        "source_load_mwh_by_node": {node: str(value) for node, value in zip(dicts["Node"], raw_energy, strict=True)},
        "source_total_storage_inflow_mwh": str(sum(inflow_energy)),
        "source_storage_inflow_mwh_by_generator": {
            unit: str(value)
            for unit, value in zip((g for g in dicts["Generation"] if g in storages), inflow_energy, strict=True)
        },
        "raw_hourly_aggregate_capacity_shortfalls": raw_capacity_shortfalls,
        "effective_aggregate_capacity_shortfalls": effective_capacity_shortfalls,
    }


def add_source_arguments(parser):
    parser.add_argument("--source-dir", required=True, type=Path, help="directory containing the 44 source CSV files")
    parser.add_argument("--license-file", required=True, type=Path, help="unmodified LICENSE from the source repository root")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_source_arguments(parser)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    tables, identity = read_package(args.source_dir, args.license_file)
    dicts, scenario_keys, step, storages, capacity, static = check_static(tables)
    result = {"audit": "fixed source inputs only", "identity": identity, "static": static,
              "time_series": check_timeseries(tables, dicts, scenario_keys, step, storages, capacity),
              "model_build": "not_run", "solve": "not_run"}
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as output:
            output.write(payload)
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
