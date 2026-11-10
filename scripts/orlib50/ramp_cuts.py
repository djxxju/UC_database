"""Add integer-valid ramp envelopes to the existing case05 model."""

from collections import defaultdict


def add_ramp_cuts(model, data):
    horizon = data["Parameters"]["Time (h)"]

    def add(name, terms):
        coefficients = defaultdict(float)
        for var, coefficient in terms:
            coefficients[var] += coefficient
        model["rows"].append({
            "name": name, "sense": "<=", "rhs": 0.0,
            "coefficients": {var: value for var, value in coefficients.items() if value},
        })

    for generator, unit in data["Generators"].items():
        points = unit["Production cost curve (MW)"]
        capacity = points[-1] - points[0]
        minimum_up = unit["Minimum uptime (h)"]
        up = unit["Ramp up limit (MW)"]
        down = unit["Ramp down limit (MW)"]
        for t in range(1, horizon + 1):
            q = [(f"lam_{generator}_{t}_{i}", point - points[0]) for i, point in enumerate(points)]
            if t > 1:
                difference = q + [
                    (f"lam_{generator}_{t-1}_{i}", points[0] - point)
                    for i, point in enumerate(points)
                ]
                add(f"ramp_on_up_{generator}_{t}", difference + [(f"u_{generator}_{t}", -up)])
                reverse = [(var, -coef) for var, coef in difference]
                add(f"ramp_on_down_{generator}_{t}", reverse + [(f"u_{generator}_{t-1}", -down)])

            cap = capacity
            if unit["Initial status (h)"] > 0:
                cap = min(cap, unit["Initial power (MW)"] - points[0] + t * up)
            # Start at hour 1 may lack a ramp from zero. Stop terms end within the source horizon.
            past = [(f"v_{generator}_{t-k}", cap - (k + 1) * up)
                    for k in range(min(minimum_up, t - 1)) if cap > (k + 1) * up]
            future = [(f"w_{generator}_{t+j}", cap - j * down)
                      for j in range(1, min(minimum_up, horizon - t) + 1) if cap > j * down]
            # The minimum-up rule makes the included start and stop events mutually exclusive.
            for k in range(len(past) + 1):
                j = min(len(future), minimum_up - k)
                if not (k or j or cap < capacity):
                    continue
                if k < len(past) and j == min(len(future), minimum_up - k - 1):
                    continue
                terms = q + [(f"u_{generator}_{t}", -cap)] + past[:k] + future[:j]
                add(f"ramp_envelope_{generator}_{t}_{k}_{j}", terms)
