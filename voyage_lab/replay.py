"""Portable exports, content identity, and numerical replay verification."""

import hashlib
import json
import math
import subprocess
from pathlib import Path

from . import MODEL_VERSION
from .core import simulate
from .models import ExportBundle, RunExport, Scenario


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def implementation_hash() -> str:
    root = Path(__file__).resolve().parent
    return digest(
        {name: (root / name).read_text(encoding="utf-8") for name in ("core.py", "models.py", "__init__.py")}
    )


def source_revision() -> str:
    try:
        root = Path(__file__).resolve().parents[1]
        if not (root / ".git").exists():
            return "source-unavailable-installed-package"
        sha = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL, timeout=2
            )
            .decode()
            .strip()
        )
        dirty = subprocess.check_output(
            [
                "git",
                "-c",
                "core.excludesFile=",
                "status",
                "--porcelain",
            ],
            cwd=root,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return sha + ("+dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        return "uncommitted-or-source-unavailable"


def hashes(scenario: Scenario) -> dict:
    data = scenario.model_dump(mode="json")
    return {name: digest(data[name]) for name in ("route", "environment", "vessel", "land")} | {
        "scenario": digest(data)
    }


def export_run(scenario: Scenario, revision: str | None = None) -> RunExport:
    return RunExport(
        model_version=MODEL_VERSION,
        source_revision=revision or source_revision(),
        implementation_sha256=implementation_hash(),
        hashes=hashes(scenario),
        scenario=scenario,
        result=simulate(scenario),
    )


def assert_equivalent(expected, actual, path="result"):
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if expected != actual:
            raise ValueError(f"Replay mismatch at {path}")
    elif isinstance(expected, (int, float)):
        if not isinstance(actual, (int, float)) or not math.isclose(
            expected, actual, rel_tol=1e-9, abs_tol=1e-6
        ):
            raise ValueError(f"Replay mismatch at {path}")
    elif isinstance(expected, dict):
        if not isinstance(actual, dict) or expected.keys() != actual.keys():
            raise ValueError(f"Replay structure mismatch at {path}")
        for key in expected:
            assert_equivalent(expected[key], actual[key], f"{path}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise ValueError(f"Replay length mismatch at {path}")
        for i, (a, b) in enumerate(zip(expected, actual)):
            assert_equivalent(a, b, f"{path}[{i}]")
    else:
        raise ValueError(f"Unsupported value at {path}")


def replay(bundle: ExportBundle) -> ExportBundle:
    runs = []
    for saved in bundle.runs:
        if saved.model_version != MODEL_VERSION:
            raise ValueError("This export requires a different scientific model version")
        if saved.hashes != hashes(saved.scenario):
            raise ValueError("Export inputs do not match their recorded hashes")
        current = export_run(saved.scenario)
        assert_equivalent(saved.result, current.result)
        runs.append(current)
    return ExportBundle(runs=runs)
