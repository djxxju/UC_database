"""Validate native IEEE24 input mapping and necessary conditions, without solving."""
import argparse
from collections import Counter
import csv
from decimal import Decimal
import gzip
import hashlib
import io
from importlib.metadata import version
import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np
import jsonschema

from build_ieee24 import CASE_ID, PROFILE, FILES, COMMIT, PROFILE_DIRECTORY, CASE_FILES

ROOT = Path(__file__).resolve().parents[1]
TOL = 1e-8


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"Non-finite JSON constant: {value}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)


def internal_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Manifest path escapes package root: {relative}")
    return path


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path, help="Defaults to ROOT/reports/ieee24_validation.json")
    args = parser.parse_args()
    root = args.root.resolve()
    case = root / "cases" / CASE_ID
    report_path = args.report or root / "reports/ieee24_validation.json"
    checks = []
    report = {"case_id": CASE_ID, "profile": PROFILE, "date": "2026-10-26", "scope": "Input structure/parameters/lossless source mapping and specified necessary conditions only", "publication_status": "unpublished", "joint_review_status": "pending", "model_execution": "not_run", "solve_status": "not_run", "independent_solution_check": "not_run", "checks": checks, "tolerance_MW": TOL, "dependencies": {"python": sys.version.split()[0], "numpy": np.__version__, "jsonschema": version("jsonschema")}}

    def check(name, ok, **detail):
        checks.append({"check_id": name, "passed": bool(ok), **detail})
        if not ok:
            raise ValueError(f"Validation failed: {name}")

    try:
        provenance = strict_json((case / "provenance.json").read_text(encoding="utf-8"))
        manifest = strict_json((root / "sources/rpglab-ieee24/manifest.json").read_text(encoding="utf-8"))
        check("profile_identity", provenance["case_id"] == CASE_ID and provenance["profile"] == PROFILE and manifest["commit"] == COMMIT)
        check("manifest_matches_provenance", manifest == provenance["source"])
        check("exact_five_pinned_originals", {f["original_name"] for f in manifest["files"]} == set(FILES) and len(manifest["files"]) == 5)
        raw = {}
        for entry in manifest["files"]:
            name = entry["original_name"]
            archive_name = name + ".gz" if name == "demand24Bus.txt" else name
            check("source_archive_path:" + name, entry["archive_path"] == "sources/rpglab-ieee24/" + archive_name)
            path = internal_path(root, entry["archive_path"])
            check("source_archive_hash:" + name, digest(path) == entry["archive_sha256"])
            payload = gzip.decompress(path.read_bytes()) if name == "demand24Bus.txt" else path.read_bytes()
            expected_hash, expected_size, _ = FILES[name]
            check("pinned_original_hash_and_size:" + name, hashlib.sha256(payload).hexdigest() == expected_hash == entry["original_sha256"] and len(payload) == expected_size == entry["original_bytes"])
            raw[name] = payload
        expected_artifacts = {f"cases/{CASE_ID}/{name}" for name in CASE_FILES - {"provenance.json"}}
        check("complete_exact_artifact_hash_manifest", set(provenance["artifact_sha256"]) == expected_artifacts)
        check("exact_six_case_delivery_files", {p.name for p in case.iterdir()} == CASE_FILES)
        expected_profile_files = {name: f"{PROFILE_DIRECTORY}/{name}.json" for name in ("field_dictionary", "model_profile")}
        check("complete_exact_profile_hash_manifest", provenance["profile_files"] == expected_profile_files and set(provenance["profile_artifact_sha256"]) == set(expected_profile_files.values()))
        check("complete_exact_script_hash_manifest", set(provenance["script_sha256"]) == {"scripts/build_ieee24.py", "scripts/validate_ieee24.py"})
        for relative, expected in provenance["artifact_sha256"].items():
            check("derived_artifact_hash:" + relative, digest(internal_path(root, relative)) == expected)
        for relative, expected in provenance["profile_artifact_sha256"].items():
            check("shared_profile_hash:" + relative, digest(internal_path(root, relative)) == expected)
        for relative, expected in provenance["script_sha256"].items():
            # Scripts may be shared from the invoking repository for an external
            # --root rebuild. Never silently accept a different script version.
            path = internal_path(root, relative)
            if not path.exists():
                path = ROOT / relative
            check("script_identity:" + relative, digest(path) == expected)
        generators = strict_json((case / "generators.json").read_text(encoding="utf-8"))
        branches = strict_json((case / "branches.json").read_text(encoding="utf-8"))
        dictionary = strict_json(internal_path(root, provenance["profile_files"]["field_dictionary"]).read_text(encoding="utf-8"))
        issues = strict_json((case / "issues.json").read_text(encoding="utf-8"))
        profile = strict_json(internal_path(root, provenance["profile_files"]["model_profile"]).read_text(encoding="utf-8"))
        schema_path = root / "schema/rpglab-ieee24-native.schema.json"
        if not schema_path.exists():
            schema_path = ROOT / "schema/rpglab-ieee24-native.schema.json"
        schema = strict_json(schema_path.read_text(encoding="utf-8"))
        instance = {"provenance": provenance, "generators": generators, "branches": branches, "issues": issues}
        jsonschema.Draft202012Validator(schema).validate(instance)
        check("json_schema_draft202012", True, schema_sha256=digest(schema_path))
        tables = {}
        for source_name, converted in (("GenData_1GPerBus.dat", generators), ("dataFileTxInfo24Bus.dat", branches)):
            source_rows = list(csv.DictReader(io.StringIO(raw[source_name].decode("utf-8-sig"))))
            equal = len(source_rows) == len(converted)
            for row, target in zip(source_rows, converted):
                equal = equal and set(row) == set(target)
                for key, value in row.items():
                    equal = equal and Decimal(value.strip()) == Decimal(str(target[key]))
            check("all_source_table_values_preserved:" + source_name, equal, records=len(source_rows), fields=len(source_rows[0]))
            tables[source_name] = source_rows
        all_fields = set(generators[0]) | set(branches[0]) | {"demand24Bus.txt"}
        check("field_dictionary_complete_unique", len(dictionary) == len(all_fields) and {f["source_field"] for f in dictionary} == all_fields)
        finite = all(math.isfinite(v) for row in generators + branches for v in row.values())
        check("all_generator_branch_values_finite", finite)
        check("generator_ids_1_to_15", [g["genNo"] for g in generators] == list(range(1, 16)))
        check("branch_ids_1_to_38", [b["branchNo"] for b in branches] == list(range(1, 39)))
        buses = set(range(1, 25))
        check("all_foreign_keys_exist", all(g["genD_bus"] in buses for g in generators) and all(b[k] in buses for b in branches for k in ("branch_fbus", "branch_tbus")))
        check("pmin_pmax_order", all(0 <= g["genD_Pmin"] <= g["genD_Pmax"] for g in generators))
        check("minimum_times_positive_integer_within_profile", all(isinstance(g[k], int) and 1 <= g[k] <= 24 for g in generators for k in ("genD_minUP", "genD_minDN")))
        check("cost_ramp_fields_nonnegative", all(g[k] >= 0 for g in generators for k in ("genC_Startup", "genC_Cost", "genC_NLoad", "SPRamp", "NSRamp", "HRamp", "StartRamp")))
        check("line_endpoints_distinct", all(b["branch_fbus"] != b["branch_tbus"] for b in branches))
        check("line_ratings_positive_ordered", all(0 < b["branch_rateA"] <= b["branch_rateC"] for b in branches))
        check("line_b_nonzero_and_source_sign_preserved", all(b["branch_b"] < 0 for b in branches), note="Negative b is observed in this pinned source, not a universal network requirement")
        adjacency = {bus: set() for bus in buses}
        pair_ids = {}
        for branch in branches:
            a, b = branch["branch_fbus"], branch["branch_tbus"]
            adjacency[a].add(b)
            adjacency[b].add(a)
            pair_ids.setdefault(tuple(sorted((a, b))), []).append(branch["branchNo"])

        def connected(group):
            group = set(group)
            seen, stack = set(), [next(iter(group))]
            while stack:
                current = stack.pop()
                if current not in seen:
                    seen.add(current)
                    stack.extend((adjacency[current] & group) - seen)
            return seen == group

        check("network_connected", connected(buses))
        parallel = [{"buses": list(pair), "branch_ids": ids} for pair, ids in pair_ids.items() if len(ids) > 1]
        check("parallel_circuits_preserved", len(pair_ids) == 34 and len(parallel) == 4 and sum(len(v) for v in pair_ids.values()) == 38, parallel_pairs=parallel)
        check("zero_capacity_record_preserved", [g["genNo"] for g in generators if g["genD_Pmax"] == 0] == [7])
        check("g13_zero_cost_source_values_preserved", all(generators[12][k] == 0 for k in ("genC_Startup", "genC_Cost", "genC_NLoad")))
        source_rows = list(csv.reader(io.StringIO(raw["demand24Bus.txt"].decode("utf-8-sig"))))
        with gzip.open(case / "demand_wide.csv.gz", "rt", encoding="utf-8", newline="") as stream:
            converted_rows = list(csv.reader(stream))
        expected_header = ["sample_id"] + [f"t{t:02d}_bus{b:02d}" for t in range(1, 25) for b in range(1, 25)]
        check("demand_column_mapping", converted_rows[0] == expected_header)
        converted_rows = converted_rows[1:]
        check("demand_dimensions", len(source_rows) == len(converted_rows) == 1800 and all(len(r) == 576 for r in source_rows) and all(len(r) == 577 for r in converted_rows))
        equal = all(target[0] == str(index) and all(a.strip() == b for a, b in zip(source, target[1:])) for index, (source, target) in enumerate(zip(source_rows, converted_rows), start=1))
        check("all_1036800_demand_lexemes_and_sample_ids_preserved", equal, numeric_values=1036800, note="Exact token equality after stripping source whitespace; no float rounding used for this check")
        loads = np.array([[float(v) for v in r[1:]] for r in converted_rows], dtype=np.float64).reshape(1800, 24, 24)
        source_loads = np.array([[float(v) for v in row] for row in source_rows], dtype=np.float64).reshape(1800, 24, 24)
        check("source_and_target_float_tensors_identical", np.array_equal(source_loads, loads))
        check("all_loads_finite_nonnegative", np.isfinite(loads).all() and (loads >= 0).all())
        check("issue_states_distinguished", {entry["status"] for entry in issues["issues"]} >= {"ambiguous", "not_collected", "not_applicable_to_cyclic_profile", "not_run"})
        check("uncollected_labels_not_claimed_missing_upstream", any("commitment24Bus.txt" in x["fields"] and x["status"] == "not_collected" for x in issues["issues"]))
        check("native_boundary_and_startup_semantics_recorded", profile["time"]["boundary"] == "cyclic_24_to_1" and profile["startup"]["no_arbitrary_v_claim"] is True and profile["network_N_minus_1_certified"] is False)
        notebook = strict_json(raw["Spatio_Temporal_UC_Acceleration_Process.ipynb"].decode("utf-8-sig"))
        source_evidence = {}
        for cell, model in ((30, "model"), (45, "modelPTDF")):
            code = "".join(notebook["cells"][cell]["source"])
            required = ["return reserve_tot_left >= reserve_tot_right", f"{model}.p_g_t[g, t] + {model}.r_g_t[g, t]", f"{model}.gen_Pmax[g] * {model}.u_g_t[g, t]", f"{model}.r_g_t[g, t] >= 0"]
            check(f"source_reserve_evidence_cell_{cell}", all(text in code for text in required))
            source_evidence[str(cell)] = hashlib.sha256(code.encode("utf-8")).hexdigest()
        btheta = "".join(notebook["cells"][30]["source"])
        check("btheta_source_flow_scaling_and_boundary_evidence", "model.p_k_t[k, t]/100" in btheta and "model.u_g_t[g, nPrd]" in btheta and "model.branch_rateA[k]" in btheta)
        totals = loads.sum(axis=2)
        pmax = np.array([g["genD_Pmax"] for g in generators], dtype=np.float64)
        capacity_limit = float(pmax.sum())
        reserve_limit = capacity_limit - float(pmax.max())
        capacity_margin = capacity_limit - totals
        reserve_margin = reserve_limit - totals
        check("capacity_necessary_condition_43200_periods", (capacity_margin >= -TOL).all(), limit_MW=capacity_limit, evaluated_periods=43200, failing_periods=int((capacity_margin < -TOL).sum()))
        check("reserve_necessary_condition_43200_periods", (reserve_margin >= -TOL).all(), limit_MW=reserve_limit, evaluated_periods=43200, failing_periods=int((reserve_margin < -TOL).sum()), derivation="sum r>=p_g+r_g -> D<=sum_{h!=g}(p_h+r_h)<=sum_{h!=g}Pmax_h, for every g; minimum is sum Pmax-max Pmax")
        local_pmax = {bus: sum(g["genD_Pmax"] for g in generators if g["genD_bus"] == bus) for bus in buses}
        cuts = []
        for size in (1, 2, 3):
            for group in itertools.combinations(sorted(buses), size):
                if connected(group):
                    boundary = [b for b in branches if (b["branch_fbus"] in group) != (b["branch_tbus"] in group)]
                    local = sum(local_pmax[b] for b in group)
                    imported = sum(b["branch_rateA"] for b in boundary)
                    cuts.append({"cut_id": len(cuts) + 1, "buses": list(group), "local_Pmax_MW": local, "boundary_rateA_sum_MW": imported, "ceiling_MW": local + imported, "boundary_branch_ids": [b["branchNo"] for b in boundary]})
        check("cut_set_enumeration", Counter(len(c["buses"]) for c in cuts) == {1: 24, 2: 34, 3: 72}, subsets=len(cuts))
        membership = np.zeros((len(cuts), 24))
        for i, cut in enumerate(cuts):
            membership[i, np.array(cut["buses"]) - 1] = 1
        cut_loads = loads.reshape(-1, 24) @ membership.T
        cut_margin = np.array([c["ceiling_MW"] for c in cuts])[None, :] - cut_loads
        check("network_cut_necessary_conditions_5616000_inequalities", (cut_margin >= -TOL).all(), evaluated_inequalities=int(cut_margin.size), failing_inequalities=int((cut_margin < -TOL).sum()))
        peak_s, peak_t = np.unravel_index(int(totals.argmax()), totals.shape)
        low_s, low_t = np.unravel_index(int(totals.argmin()), totals.shape)
        row, column = np.unravel_index(int(cut_margin.argmin()), cut_margin.shape)
        cut = cuts[column]
        sample_id, period = row // 24 + 1, row % 24 + 1
        check("decimal_control_peak_load", abs(float(sum((Decimal(v.strip()) for v in source_rows[peak_s][peak_t * 24:(peak_t + 1) * 24]), Decimal(0))) - float(totals[peak_s, peak_t])) < TOL)
        results = {"capacity_limit_MW": capacity_limit, "reserve_necessary_limit_MW": reserve_limit, "peak": {"sample_id": int(peak_s + 1), "period": int(peak_t + 1), "load_MW": float(totals[peak_s, peak_t]), "capacity_margin_MW": float(capacity_margin[peak_s, peak_t]), "reserve_bound_margin_MW": float(reserve_margin[peak_s, peak_t])}, "minimum_load": {"sample_id": int(low_s + 1), "period": int(low_t + 1), "load_MW": float(totals[low_s, low_t])}, "network_worst": {"sample_id": int(sample_id), "period": int(period), "cut": cut, "area_load_MW": float(cut_loads[row, column]), "margin_MW": float(cut_margin[row, column])}, "cuts": cuts}
        per_sample = root / "reports/ieee24_per_sample_checks.csv"
        per_sample.parent.mkdir(parents=True, exist_ok=True)
        with per_sample.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["sample_id", "peak_load_MW", "capacity_min_margin_MW", "reserve_bound_min_margin_MW", "network_cut_min_margin_MW", "capacity_failed_periods", "reserve_failed_periods", "network_failed_inequalities"])
            for s in range(1800):
                margins = cut_margin[s * 24:(s + 1) * 24]
                writer.writerow([s + 1, float(totals[s].max()), float(capacity_margin[s].min()), float(reserve_margin[s].min()), float(margins.min()), int((capacity_margin[s] < -TOL).sum()), int((reserve_margin[s] < -TOL).sum()), int((margins < -TOL).sum())])
        report.update({"results": results, "source_cell_sha256": source_evidence, "per_sample_report_sha256": digest(per_sample), "data_shape": list(loads.shape), "status": "passed_data_checks_only", "source_commit": COMMIT, "issues_status_counts": dict(Counter(x["status"] for x in issues["issues"])), "limitations": ["Passing necessary inequalities is not a UC or DC-flow feasibility proof.", "No generation schedule, startup/ramp/reserve delivery or optimality has been validated.", "Author PTDF matrix and ML/result labels are not collected in this package.", "No COPT/Gurobi, source Notebook or full model was executed.", "Package is local, unpublished and pending joint review."]})
    except Exception as exc:
        report.update({"status": "failed", "error_type": type(exc).__name__, "error": str(exc)})
        write_json(report_path, report)
        print(json.dumps({"status": "failed", "error": str(exc), "report": str(report_path)}, ensure_ascii=False))
        return 1
    report["passed_check_count"] = sum(c["passed"] for c in checks)
    write_json(report_path, report)
    print(json.dumps({"status": report["status"], "passed_checks": report["passed_check_count"], "source_values": 1036800, "network_cut_inequalities": 5616000, "report": str(report_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
