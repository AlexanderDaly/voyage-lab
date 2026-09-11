"""A small measured suite, with no forecast or real-vessel accuracy claims."""

import json
import platform
import time
from datetime import timedelta
from pathlib import Path

from voyage_lab import MODEL_VERSION
from voyage_lab.core import KNOT, simulate
from voyage_lab.fixtures import FIXTURES, START, default_scenario, load_environment
from voyage_lab.models import Scenario
from voyage_lab.replay import implementation_hash, source_revision


def main():
    rows = []
    for fixture in FIXTURES:
        for speed in (10, 12, 14):
            base = default_scenario().model_dump() | {
                "environment": load_environment(fixture),
                "speed_mps": speed * KNOT,
            }
            scenario = Scenario.model_validate(base)
            started = time.perf_counter()
            result = simulate(scenario)
            runtime = time.perf_counter() - started
            rows.append(
                {
                    "fixture": fixture,
                    "speed_knots": speed,
                    "runtime_s": runtime,
                    **{k: v for k, v in result.items() if k != "trajectory"},
                }
            )
    base = default_scenario()
    convergence = []
    for step in (900, 450, 225):
        result = simulate(Scenario.model_validate(base.model_dump() | {"max_step_s": step}))
        convergence.append({"step_s": step, **{k: result[k] for k in ("elapsed_s", "fuel_kg", "total_cost")}})
    tight = simulate(Scenario.model_validate(base.model_dump() | {"deadline": START + timedelta(hours=24)}))
    report = {
        "model_version": MODEL_VERSION,
        "implementation_sha256": implementation_hash(),
        "source_revision": source_revision(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "runs": rows,
        "convergence": convergence,
        "infeasible_deadline": {k: v for k, v in tight.items() if k != "trajectory"},
        "interpretation": "Implementation and synthetic sensitivity evidence only. Runtime covers core simulation; no I/O. No optimizer or empirical accuracy benchmark.",
    }
    path = Path("benchmarks/results.json")
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} runs and convergence results to {path}")


if __name__ == "__main__":
    main()
