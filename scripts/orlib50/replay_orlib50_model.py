"""Rebuild and verify the OR-LIB 50 reference formulation without a solver."""

import json
from pathlib import Path

from ramp_cuts import add_ramp_cuts
from solve_compare import canonical, sha
from uc_model import build_model

ROOT = Path(__file__).resolve().parents[2]
CASE_ID = "orlib_50_0_1_w"


def main():
    source = (ROOT / "cases" / CASE_ID / "input.json").read_bytes()
    manifest = json.loads((ROOT / "results" / CASE_ID / "run_manifest.json").read_bytes())
    if sha(source) != manifest["decompressed_sha256"]:
        raise ValueError("Input SHA256 differs from the reference run")

    data = json.loads(source)
    model = build_model(data)
    base_hash = sha(canonical(model))
    original_rows = len(model["rows"])
    add_ramp_cuts(model, data)
    checks = {
        "base_model_sha256": base_hash,
        "model_sha256": sha(canonical(model)),
        "rows": len(model["rows"]),
        "model_variables": len(model["variables"]),
        "binary_variables": sum(var["type"] == "B" for var in model["variables"].values()),
        "ramp_cut_count": len(model["rows"]) - original_rows,
    }
    for name, value in checks.items():
        if value != manifest[name]:
            raise ValueError(f"Reference formulation mismatch for {name}: {value}")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
