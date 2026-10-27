"""Independently check a candidate against the author's cyclic B-theta UC rules.

This program never solves, rounds, repairs, or completes a candidate. It checks
all supplied p/u/v/r/flow/theta values and recomputes the linear objective.
"""
import argparse
import csv
from decimal import Decimal
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "rpglab_ieee24_native_v1"
SOURCE_COMMIT = "d9fb2a1c92c86b9d16c8fa30372b74cd3c86d89e"
DEFAULT_TOLERANCES = {
    "MW": 1e-5, "binary": 1e-6, "logic": 1e-6,
    "angle_reference": 1e-7, "objective_absolute": 1e-4,
    "objective_relative": 1e-8,
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("Non-finite JSON literal: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=unique, parse_constant=invalid)


def expected_variables(generators, branches, buses, horizon):
    result = []
    for g in generators:
        for t in range(1, horizon + 1):
            result.extend(f"{kind}_{g['genNo']}_{t}" for kind in ("p", "u", "v", "r"))
    for branch in branches:
        result.extend(f"f_{branch['branchNo']}_{t}" for t in range(1, horizon + 1))
    for bus in buses:
        result.extend(f"theta_{bus}_{t}" for t in range(1, horizon + 1))
    return result


def check_candidate(generators, branches, loads, values, *, objective_value=None,
                    tolerances=None, max_failure_examples=40):
    """Pure numeric checker, also usable with clearly synthetic small fixtures.

    loads maps one-based bus IDs to period arrays. values is a complete flat
    variable-name -> finite numeric value dictionary. No solver APIs are used.
    """
    tol = dict(DEFAULT_TOLERANCES)
    if tolerances:
        tol.update(tolerances)
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0 for v in tol.values()):
        raise ValueError("All declared tolerances must be finite nonnegative numbers")
    if not loads or 1 not in loads:
        raise ValueError("The author's reference bus 1 must be present")
    buses = sorted(loads)
    horizon = len(loads[buses[0]])
    if horizon < 1 or any(len(loads[n]) != horizon for n in buses):
        raise ValueError("Load horizon mismatch")
    if any(not math.isfinite(x) for n in buses for x in loads[n]):
        raise ValueError("Non-finite source load")
    gids = [g["genNo"] for g in generators]
    bids = [b["branchNo"] for b in branches]
    if len(set(gids)) != len(gids) or len(set(bids)) != len(bids):
        raise ValueError("Duplicate generator or branch ID")
    for g in generators:
        if g["genD_bus"] not in loads:
            raise ValueError("Unknown generator bus")
        for field in ("genD_minUP", "genD_minDN"):
            if type(g[field]) is not int or not 1 <= g[field] <= horizon:
                raise ValueError("Author cyclic window requires 1 <= minimum time <= horizon")
        for field in ("genD_Pmin", "genD_Pmax", "SPRamp", "HRamp", "StartRamp", "genC_Cost", "genC_NLoad", "genC_Startup"):
            if not isinstance(g[field], (float, int)) or isinstance(g[field], bool) or not math.isfinite(g[field]):
                raise ValueError("Non-finite generator parameter: " + field)
    for b in branches:
        if b["branch_fbus"] not in loads or b["branch_tbus"] not in loads:
            raise ValueError("Unknown branch bus")
        if not all(isinstance(b[k], (float, int)) and not isinstance(b[k], bool) and math.isfinite(b[k]) for k in ("branch_b", "branch_rateA")):
            raise ValueError("Non-finite branch parameter")
    required = set(expected_variables(generators, branches, buses, horizon))
    if not isinstance(values, dict):
        raise ValueError("Candidate values must be an object")
    missing = sorted(required - set(values))
    invalid_values = [k for k in sorted(values)
                      if isinstance(values[k], bool) or not isinstance(values[k], (int, float)) or not math.isfinite(values[k])]
    result = {
        "status": "invalid_candidate", "passed": False,
        "scope": "Candidate feasibility and objective recomputation for the author's cyclic B-theta formulation only",
        "optimality_proven": False, "solver_called": False,
        "tolerances": tol, "required_variable_count": len(required),
        "missing_variables": missing, "invalid_or_nonfinite_variables": invalid_values,
        "extra_variable_names": sorted(set(values) - required),
        "constraint_groups": {}, "failure_examples": [],
    }
    if missing or invalid_values:
        return result
    if objective_value is not None and (isinstance(objective_value, bool) or not isinstance(objective_value, (int, float)) or not math.isfinite(objective_value)):
        result["invalid_reported_objective"] = True
        return result
    groups = result["constraint_groups"]
    def record(name, residual, tolerance, location, *, equality=False):
        if not math.isfinite(residual):
            raise ValueError("Non-finite arithmetic while checking " + name)
        violation = abs(residual) if equality else max(0.0, residual)
        entry = groups.setdefault(name, {"evaluations": 0, "failing_evaluations": 0,
                                        "max_violation": 0.0, "tolerance": tolerance,
                                        "worst_location": None})
        entry["evaluations"] += 1
        if violation > entry["max_violation"] or entry["worst_location"] is None:
            entry["max_violation"] = violation
            entry["worst_location"] = location
        if violation > tolerance:
            entry["failing_evaluations"] += 1
            if len(result["failure_examples"]) < max_failure_examples:
                result["failure_examples"].append({"group": name, "location": location,
                                                   "violation": violation, "tolerance": tolerance,
                                                   "signed_residual": residual})
    def val(kind, entity, t):
        return float(values[f"{kind}_{entity}_{t}"])
    wrap = lambda t: (t - 1) % horizon + 1
    generation_cost, no_load_cost, startup_cost = [], [], []
    for t in range(1, horizon + 1):
        total_r = math.fsum(val("r", g, t) for g in gids)
        for g in generators:
            gid, prev = g["genNo"], wrap(t - 1)
            p, u, v, r = (val(k, gid, t) for k in ("p", "u", "v", "r"))
            pp, uprev = val("p", gid, prev), val("u", gid, prev)
            location = {"generator_id": gid, "period": t}
            for kind, binary in (("u", u), ("v", v)):
                record("binary_variables", min(abs(binary), abs(binary - 1)), tol["binary"], {**location, "variable": kind})
            record("minimum_output", g["genD_Pmin"] * u - p, tol["MW"], location)
            record("capacity_with_reserve", p + r - g["genD_Pmax"] * u, tol["MW"], location)
            record("reserve_response_cap", r - g["SPRamp"] * u, tol["MW"], location)
            record("reserve_nonnegative", -r, tol["MW"], location)
            record("author_per_generator_total_reserve", p + r - total_r, tol["MW"], location)
            # Preserve the source asymmetry: wrap hour uses u_previous, other
            # hours use u_current. Do not replace by a textbook ramp formula.
            ramp_u = uprev if t == 1 else u
            record("ramp_up", p - pp - g["HRamp"] * ramp_u - g["StartRamp"] * v, tol["MW"], location)
            record("ramp_down", pp - p - g["HRamp"] * u - g["StartRamp"] * (v - u + uprev), tol["MW"], location)
            min_up = math.fsum(val("v", gid, wrap(t - j)) for j in range(g["genD_minUP"]))
            min_down = math.fsum(val("v", gid, wrap(t + j)) for j in range(1, g["genD_minDN"] + 1))
            record("cyclic_minimum_up", min_up - u, tol["logic"], location)
            record("cyclic_minimum_down", min_down - (1 - u), tol["logic"], location)
            record("startup_lower_bound", u - uprev - v, tol["logic"], location)
            generation_cost.append(g["genC_Cost"] * p)
            no_load_cost.append(g["genC_NLoad"] * u)
            startup_cost.append(g["genC_Startup"] * v)
        record("reference_angle", val("theta", 1, t), tol["angle_reference"], {"bus_id": 1, "period": t}, equality=True)
        for b in branches:
            bid = b["branchNo"]
            flow = val("f", bid, t)
            delta = val("theta", b["branch_tbus"], t) - val("theta", b["branch_fbus"], t)
            location = {"branch_id": bid, "period": t}
            record("dc_flow_equation_MW", 100 * b["branch_b"] * delta - flow, tol["MW"], location, equality=True)
            record("normal_line_upper", flow - b["branch_rateA"], tol["MW"], location)
            record("normal_line_lower", -flow - b["branch_rateA"], tol["MW"], location)
        for n in buses:
            produced = math.fsum(val("p", g["genNo"], t) for g in generators if g["genD_bus"] == n)
            incoming = math.fsum(val("f", b["branchNo"], t) for b in branches if b["branch_tbus"] == n)
            outgoing = math.fsum(val("f", b["branchNo"], t) for b in branches if b["branch_fbus"] == n)
            record("nodal_balance_MW", produced + incoming - outgoing - loads[n][t - 1], tol["MW"], {"bus_id": n, "period": t}, equality=True)
    components = {"generation": math.fsum(generation_cost), "no_load": math.fsum(no_load_cost), "startup": math.fsum(startup_cost)}
    objective = math.fsum(components.values())
    if not math.isfinite(objective):
        raise ValueError("Non-finite objective recomputation")
    objective_tolerance = tol["objective_absolute"] + tol["objective_relative"] * abs(objective)
    if objective_value is not None:
        record("reported_objective", float(objective_value) - objective, objective_tolerance, {"item": "total_objective"}, equality=True)
    failures = sum(entry["failing_evaluations"] for entry in groups.values())
    result.update({"status": "feasible_within_declared_tolerances" if not failures else "constraint_violations",
                   "passed": not failures, "failing_evaluations": failures,
                   "constraint_evaluations": sum(entry["evaluations"] for entry in groups.values()),
                   "objective": {"recomputed": objective, "components": components,
                                 "reported": objective_value,
                                 "comparison": "not_provided" if objective_value is None else "checked",
                                 "comparison_tolerance": objective_tolerance},
                   "limitations": ["No optimality certificate is checked; this is not an optimality proof.",
                                   "No line-contingency or reactive-power model is added.",
                                   "Values are checked as supplied without rounding or repair."]})
    return result


def confined(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Input path outside repository")
    return path


def load_case(case_dir, sample_id):
    """Read a selected source-identified sample, independently of the model builder."""
    case = Path(case_dir).resolve()
    root = case.parents[1]
    p = load_json(case / "provenance.json")
    if p["case_id"] != CASE_ID or p["source"]["commit"] != SOURCE_COMMIT:
        raise ValueError("Unsupported case/source identity")
    for name in ("generators.json", "branches.json", "demand_wide.csv.gz"):
        relative = (case / name).relative_to(root).as_posix()
        if sha(case / name) != p["artifact_sha256"][relative]:
            raise ValueError("Input artifact hash mismatch: " + name)
    gens, branches = load_json(case / "generators.json"), load_json(case / "branches.json")
    shape = p["shape"]
    if type(sample_id) is not int or not 1 <= sample_id <= shape["samples"]:
        raise ValueError("sample_id must identify an original one-based row")
    if (shape["generators"], shape["branches"], shape["buses"], shape["periods_per_sample"]) != (15, 38, 24, 24):
        raise ValueError("Unsupported native shape")
    with gzip.open(case / "demand_wide.csv.gz", "rt", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if header != ["sample_id"] + [f"t{t:02d}_bus{n:02d}" for t in range(1, 25) for n in range(1, 25)]:
            raise ValueError("Demand column mapping mismatch")
        target = None
        for i, row in enumerate(reader, start=1):
            if i == sample_id:
                target = row
                break
    if target is None or len(target) != 577 or target[0] != str(sample_id):
        raise ValueError("Missing/misaligned selected sample")
    source_hashes = {}
    source_payload = {}
    for entry in p["source"]["files"]:
        name = entry["original_name"]
        path = confined(root, entry["archive_path"])
        if sha(path) != entry["archive_sha256"]:
            raise ValueError("Source archive hash mismatch: " + name)
        payload = gzip.decompress(path.read_bytes()) if name == "demand24Bus.txt" else path.read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        if actual != entry["original_sha256"]:
            raise ValueError("Original identity mismatch: " + name)
        source_hashes[name] = actual
        source_payload[name] = payload
    for name, converted in (("GenData_1GPerBus.dat", gens), ("dataFileTxInfo24Bus.dat", branches)):
        original = list(csv.DictReader(io.StringIO(source_payload[name].decode("utf-8-sig"))))
        if len(original) != len(converted):
            raise ValueError("Source table row count mismatch")
        for a, b in zip(original, converted):
            if set(a) != set(b) or any(Decimal(v.strip()) != Decimal(str(b[k])) for k, v in a.items()):
                raise ValueError("Source table value mismatch: " + name)
    original_row = next(row for i, row in enumerate(csv.reader(io.StringIO(source_payload["demand24Bus.txt"].decode("utf-8-sig"))), start=1) if i == sample_id)
    if [v.strip() for v in original_row] != target[1:]:
        raise ValueError("Selected load sample does not preserve original values")
    loads = {n: [float(target[1 + (t - 1) * 24 + n - 1]) for t in range(1, 25)] for n in range(1, 25)}
    metadata = {"case_id": CASE_ID, "sample_id": sample_id, "source_commit": SOURCE_COMMIT,
                "source_sha256": source_hashes,
                "input_sha256": {name: sha(case / name) for name in ("generators.json", "branches.json", "demand_wide.csv.gz", "provenance.json")},
                "original_notebook_cell_zero_based": 30,
                "notebook_cell_sha256": hashlib.sha256("".join(json.loads(source_payload["Spatio_Temporal_UC_Acceleration_Process.ipynb"].decode("utf-8-sig"))["cells"][30]["source"]).encode("utf-8")).hexdigest()}
    return gens, branches, loads, metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, default=ROOT / "cases" / CASE_ID)
    parser.add_argument("--sample-id", type=int, default=1)
    parser.add_argument("--solution", type=Path, required=True, help="Complete flat variable-name to numeric-value JSON")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--objective-value", type=float)
    parser.add_argument("--feasibility-tol-mw", type=float, default=DEFAULT_TOLERANCES["MW"])
    parser.add_argument("--binary-tol", type=float, default=DEFAULT_TOLERANCES["binary"])
    args = parser.parse_args(argv)
    report_path = args.report or args.solution.parent / "independent_validation.json"
    try:
        generators, branches, loads, metadata = load_case(args.case_dir, args.sample_id)
        candidate = load_json(args.solution)
        if "values" in candidate:
            if candidate.get("sample_id", args.sample_id) != args.sample_id or candidate.get("case_id", CASE_ID) != CASE_ID:
                raise ValueError("Candidate metadata does not match requested case/sample")
            objective = args.objective_value if args.objective_value is not None else candidate.get("objective_value")
            values = candidate["values"]
        else:
            values, objective = candidate, args.objective_value
        report = check_candidate(generators, branches, loads, values, objective_value=objective,
                                 tolerances={"MW": args.feasibility_tol_mw, "binary": args.binary_tol})
        report.update(metadata)
        report.update({"candidate_sha256": sha(args.solution), "checker_sha256": sha(Path(__file__)),
                       "python_version": sys.version.split()[0]})
    except Exception as exc:
        report = {"status": "check_error", "passed": False, "optimality_proven": False,
                  "solver_called": False, "error_type": type(exc).__name__, "error": str(exc),
                  "sample_id": args.sample_id, "checker_sha256": sha(Path(__file__))}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["status"], "passed": report["passed"],
                      "report": str(report_path)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
