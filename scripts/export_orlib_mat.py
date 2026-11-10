"""Convert one OR-LIB UC.jl JSON file to MAT. With no arguments, open a file picker."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

import numpy as np
from scipy.io import savemat



def cell(values):
    result = np.empty((len(values), 1), dtype=object)
    for i, value in enumerate(values):
        result[i, 0] = value
    return result


def struct_rows(rows):
    result = np.empty((len(rows), 1), dtype=[(key, object) for key in rows[0]])
    for i, row in enumerate(rows):
        for key, value in row.items():
            result[key][i, 0] = value
    return result


def numbers(values):
    result = np.asarray(values, dtype=np.float64)
    if not np.isfinite(result).all():
        raise ValueError("Unexpected nonfinite numeric input")
    return result


ORLIB_FIELDS = {
    "initial_status_h": "Initial status (h)",
    "initial_power_MW": "Initial power (MW)",
    "min_up_h": "Minimum uptime (h)",
    "min_down_h": "Minimum downtime (h)",
    "ramp_up_MW": "Ramp up limit (MW)",
    "ramp_down_MW": "Ramp down limit (MW)",
    "production_cost_MW": "Production cost curve (MW)",
    "production_cost": "Production cost curve ($)",
    "startup_delay_h": "Startup delays (h)",
    "startup_cost": "Startup costs ($)",
}


def load_orlib(text):
    raw = json.loads(text)
    hours = raw["Parameters"]["Time (h)"]
    if hours != 24 or len(raw["Buses"]) != 1 or len(raw["Reserves"]) != 1:
        raise ValueError("Expected the OR-LIB single-node, one-reserve, 24-hour profile")
    bus, bus_record = next(iter(raw["Buses"].items()))
    reserve, reserve_record = next(iter(raw["Reserves"].items()))
    if reserve_record["Type"] != "Spinning":
        raise ValueError("Expected spinning reserve")
    demand = numbers(bus_record["Load (MW)"])
    reserve_amount = numbers(reserve_record["Amount (MW)"])
    if demand.shape != (hours,) or reserve_amount.shape != (hours,):
        raise ValueError("Expected 24 explicit load and reserve entries")

    if not isinstance(raw["Generators"], dict) or not raw["Generators"]:
        raise ValueError("Expected at least one generator")
    generators = []
    for key, gen in raw["Generators"].items():
        if gen["Bus"] != bus:
            raise ValueError(f"Generator {key} references an unknown bus")
        record = {"id": key, "bus_id": bus,
                  "reserve_eligibility": cell(gen["Reserve eligibility"])}
        record.update({field: numbers(gen[source]) for field, source in ORLIB_FIELDS.items()})
        for a, b in (("production_cost_MW", "production_cost"), ("startup_delay_h", "startup_cost")):
            if not record[a].size or record[a].ndim != 1 or record[a].shape != record[b].shape:
                raise ValueError(f"Unpaired cost or startup points for {key}")
        generators.append(record)

    return dict(
        demand_MW=demand, demand_axes="time,bus", bus_id=cell([bus]),
        reserve_MW=reserve_amount, reserve_id=cell([reserve]),
        reserve_type=reserve_record["Type"], time_hour=np.arange(1, hours + 1),
        time_step_h=1, generators=struct_rows(generators), source_json=text,
    )


def export_mat(source, output):
    """Convert source JSON(.gz) without modifying it or replacing an existing MAT file."""
    source, output = Path(source), Path(output)
    if not source.name.lower().endswith((".json", ".json.gz")):
        raise ValueError("Choose an OR-LIB .json or .json.gz file")
    if output.suffix.lower() != ".mat":
        raise ValueError("Output must have a .mat extension")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    original = source.read_bytes()
    payload = gzip.decompress(original) if source.suffix.lower() == ".gz" else original
    data = load_orlib(payload.decode("utf-8-sig"))
    case_id = source.parent.name if source.name == "input.json" else source.name.split(".")[0]
    uc = dict(
        schema_version="uc-bench-mat/1.0", profile="orlib", case_id=case_id,
        sources=struct_rows([{"name": source.name, "sha256": hashlib.sha256(original).hexdigest()}]),
        **data,
    )

    # Stage beside the destination so the result inherits its directory's access rules.
    with NamedTemporaryFile(dir=output.parent, suffix=".mat", delete=False) as staging:
        temp = Path(staging.name)
    try:
        savemat(temp, {"uc": uc}, long_field_names=True, do_compression=True, oned_as="column")
        output.hardlink_to(temp)
    finally:
        temp.unlink()
    return output


def open_picker():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    def choose():
        source = filedialog.askopenfilename(parent=window, title="选择 OR-LIB JSON 文件",
                                            filetypes=[("JSON", ("*.json", "*.json.gz"))])
        if not source:
            return
        source = Path(source)
        name = source.parent.name if source.name == "input.json" else source.name.split(".")[0]
        output = filedialog.asksaveasfilename(parent=window, title="保存 MATLAB 文件",
                                              initialfile=f"{name}.mat", defaultextension=".mat",
                                              filetypes=[("MATLAB", "*.mat")])
        if not output:
            return
        try:
            result = export_mat(source, output)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("转换失败", str(error), parent=window)
        else:
            messagebox.showinfo("转换完成", str(result.resolve()), parent=window)

    window = tk.Tk()
    window.title("UC-Bench JSON 转 MAT")
    tk.Label(window, text="OR-LIB 单节点 24 小时算例").pack(padx=24, pady=(24, 8))
    tk.Button(window, text="选择 JSON 并另存 MAT", command=choose).pack(padx=24, pady=(8, 24))
    window.mainloop()


def main():
    if len(sys.argv) == 1:
        open_picker()
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        print(export_mat(args.source, args.output))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Conversion failed: {error}\n")


if __name__ == "__main__":
    main()
