"""Deterministic fixture authoring and local catalog. No live weather access."""

import json
import math
from datetime import datetime, timedelta, timezone
from importlib.resources import files

from .core import KNOT
from .models import FIELDS, Environment, Route, Scenario, Vessel, utc_string

START = datetime(2026, 9, 11, tzinfo=timezone.utc)
ROUTES = [
    Route(
        id="offshore",
        name="Offshore passage",
        coordinates=[
            (-125.4, 48.1),
            (-125.6, 46),
            (-125.3, 43),
            (-125.0, 40.5),
            (-123.6, 38),
            (-122.0, 35.5),
            (-120.8, 34.1),
            (-119.1, 33.3),
        ],
    ),
    Route(
        id="outer",
        name="Outer passage",
        coordinates=[
            (-125.4, 48.1),
            (-126.5, 46),
            (-126.4, 43),
            (-126.0, 40.5),
            (-124.5, 38),
            (-122.8, 35.5),
            (-121.0, 33.4),
            (-119.1, 33.3),
        ],
    ),
]
FIXTURES = {
    "moving-storm": "Moving storm",
    "calm": "Calm water",
    "head-seas": "Persistent head seas",
    "following-current": "Following current",
    "opposing-current": "Opposing current",
}


def make_environment(name: str) -> Environment:
    if name not in FIXTURES:
        raise ValueError("Unknown fixture")
    lats, lons = [30.0, 34.0, 38.0, 42.0, 46.0, 50.0], [-130.0, -126.0, -122.0, -116.0]
    times = [START + timedelta(hours=h) for h in range(0, 241, 6)]
    fields = {f: [] for f in sorted(FIELDS)}
    for time in times:
        h = (time - START).total_seconds() / 3600
        plane = {f: [] for f in fields}
        for lat in lats:
            row = {f: [] for f in fields}
            for lon in lons:
                storm = math.exp(-(((lat - (44 - h * 0.045)) / 3.0) ** 2) - ((lon + 125) / 4) ** 2)
                values = {f: 0.0 for f in fields}
                values["wave_from_north"] = -1.0
                if name == "moving-storm":
                    values.update(
                        wave_height_m=0.7 + 4.5 * storm,
                        wind_north_mps=4 + 16 * storm,
                        current_east_mps=0.2 * math.sin(h / 18 + lat),
                        current_north_mps=-0.3 + 0.3 * math.sin(h / 24 + lon),
                    )
                elif name == "head-seas":
                    values.update(wave_height_m=4.0, wind_north_mps=14.0)
                elif name.endswith("current"):
                    values["current_north_mps"] = -0.7 if name.startswith("following") else 0.7
                for f in fields:
                    row[f].append(round(values[f], 8))
            for f in fields:
                plane[f].append(row[f])
        for f in fields:
            fields[f].append(plane[f])
    return Environment(
        id=name, name=FIXTURES[name], times=times, latitudes=lats, longitudes=lons, fields=fields
    )


def load_environment(name: str) -> Environment:
    if name not in FIXTURES:
        raise ValueError("Unknown fixture")
    return Environment.model_validate_json(
        files("voyage_lab").joinpath(f"data/{name}.json").read_text(encoding="utf-8")
    )


def default_scenario() -> Scenario:
    land = json.loads(files("voyage_lab").joinpath("data/land.geojson").read_text(encoding="utf-8"))
    return Scenario(
        departure=START,
        deadline=START + timedelta(hours=100),
        speed_mps=12 * KNOT,
        vessel=Vessel(),
        route=ROUTES[0],
        environment=load_environment("moving-storm"),
        land=land,
    )


def write_fixtures():
    from pathlib import Path

    dest = Path(__file__).parent / "data"
    dest.mkdir(exist_ok=True)
    for name in FIXTURES:
        (dest / f"{name}.json").write_text(make_environment(name).model_dump_json(), encoding="utf-8")
    (dest / "fixture-provenance.json").write_text(
        json.dumps(
            {
                "generator": "voyage_lab.fixtures.make_environment",
                "version": 1,
                "kind": "synthetic",
                "valid_from": utc_string(START),
                "valid_to": utc_string(START + timedelta(hours=240)),
                "units": {
                    f: "m"
                    if f == "wave_height_m"
                    else "unit vector (from)"
                    if f.startswith("wave_from")
                    else "m/s (to)"
                    for f in FIELDS
                },
                "license": "MIT",
                "seed": None,
                "issue_time": None,
                "retrieval_time": None,
                "note": "Original analytic fields sampled every 6 hours on a coarse grid. Not observations or forecasts.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    write_fixtures()
