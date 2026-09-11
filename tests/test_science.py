"""Independent physical checks and failure-mode regression tests."""

import copy
import math
from datetime import timedelta

import pytest
from pydantic import ValidationError
from shapely.geometry import box, mapping

from voyage_lab.core import GEOD, KNOT, ModelFailure, Sampler, effective_water_speed, ground_speed, simulate
from voyage_lab.fixtures import ROUTES, START, default_scenario, load_environment
from voyage_lab.models import Environment, ExportBundle, Route, Scenario, Vessel
from voyage_lab.replay import export_run, replay


@pytest.fixture
def hand():
    # WGS84 geodesic length constructed independently of the integration loop.
    start = (-129, 35)
    lon, lat, _ = GEOD.fwd(*start, 0, 240 * 1852)
    return Scenario(
        name="240 nautical mile hand check",
        departure=START,
        deadline=START + timedelta(days=2),
        speed_mps=10 * KNOT,
        vessel=Vessel(),
        route=Route(id="hand", name="240 nm fixture", coordinates=[start, (lon, lat)]),
        environment=load_environment("calm"),
        land={"type": "MultiPolygon", "coordinates": []},
    )


def changed(scenario, **patch):
    return Scenario.model_validate(scenario.model_dump() | patch)


def test_hand_calculation(hand):
    result = simulate(hand)
    assert result["status"] == "completed"
    assert result["elapsed_s"] == pytest.approx(86400, abs=1e-6)
    assert result["distance_m"] == pytest.approx(240 * 1852, abs=1e-6)
    assert result["fuel_kg"] == pytest.approx(22000, abs=1e-6)
    assert result["fuel_cost"] == pytest.approx(13200)
    assert result["time_cost"] == pytest.approx(12000)
    assert result["total_cost"] == pytest.approx(25200)
    assert result["trajectory"][-1]["cost"] == result["total_cost"]


@pytest.mark.parametrize(
    "bearing,east,north,expected",
    [
        (0, 0, 1, 6),
        (0, 0, -1, 4),
        (90, 1, 0, 6),
        (180, 0, -1, 6),
        (0, 3, 0, 4),
        (0, -3, 0, 4),
        (90, 0, 3, 4),
        (0, 3, 1, 5),
    ],
)
def test_current_direction_and_track_holding(bearing, east, north, expected):
    assert ground_speed(5, east, north, bearing) == pytest.approx(expected)


@pytest.mark.parametrize(
    "east,north,code", [(5.1, 0, "cross_current"), (0, -5, "no_progress"), (0, -6, "no_progress")]
)
def test_impossible_currents(east, north, code):
    with pytest.raises(ModelFailure) as error:
        ground_speed(5, east, north, 0)
    assert error.value.code == code


def test_auxiliary_and_cubic_consumption(hand):
    fast = simulate(changed(hand, speed_mps=20 * KNOT / 1.5))
    v = 20 / 1.5
    expected_days = 240 / v / 24
    assert fast["fuel_kg"] == pytest.approx((20000 * (v / 10) ** 3 + 2000) * expected_days)


def test_fixed_cost_and_deadline_preserve_complete_metrics(hand):
    result = simulate(changed(hand, fixed_cost=1700, deadline=START + timedelta(hours=23)))
    assert result["completed"] and not result["deadline_met"]
    assert result["status"] == "deadline_exceeded"
    assert result["total_cost"] == pytest.approx(26900)
    assert result["eta"] is not None


def test_current_affects_time_but_not_commanded_fuel_rate(hand):
    env = hand.environment.model_dump()
    for plane in env["fields"]["current_north_mps"]:
        for row in plane:
            row[:] = [1.0] * len(row)
    result = simulate(changed(hand, environment=env))
    elapsed = 240 * 1852 / (10 * KNOT + 1)
    assert result["elapsed_s"] == pytest.approx(elapsed)
    assert result["fuel_kg"] == pytest.approx(22000 * elapsed / 86400)


def test_weather_direction_and_loss_bound(hand):
    env = Sampler(load_environment("head-seas")).sample(-129, 35, START.timestamp())
    north = effective_water_speed(hand, env, 0)
    south = effective_water_speed(hand, env, 180)
    assert south < north < hand.speed_mps
    env["wave_height_m"] = 100
    assert effective_water_speed(hand, env, 180) == pytest.approx(
        hand.speed_mps * (1 - hand.vessel.max_speed_loss)
    )


def test_direction_interpolation_across_north(hand):
    env = hand.environment.model_dump()
    for f in ("wave_from_east", "wave_from_north"):
        for ti, plane in enumerate(env["fields"][f]):
            angle = math.radians(350 if ti == 0 else 10)
            for row in plane:
                row[:] = [math.sin(angle) if f.endswith("east") else math.cos(angle)] * len(row)
    sampled = Sampler(Environment.model_validate(env)).sample(
        -129, 35, (START + timedelta(hours=3)).timestamp()
    )
    assert sampled["wave_from_east"] == pytest.approx(0, abs=1e-12)
    assert sampled["wave_from_north"] > 0.98


def test_time_dependent_environment_and_departure():
    base = default_scenario()
    first = simulate(base)
    later = simulate(changed(base, departure=START + timedelta(hours=18), deadline=START + timedelta(days=7)))
    assert first["elapsed_s"] != pytest.approx(later["elapsed_s"], rel=0.001)
    assert len(set(round(p["wave_height_m"], 3) for p in first["trajectory"])) > 20
    slow = simulate(changed(base, speed_mps=10 * KNOT))
    # Independent sampling at the first moving step of the slower vessel.
    point = slow["trajectory"][1]
    sample = Sampler(base.environment).sample(
        point["lon"], point["lat"], START.timestamp() + point["elapsed_s"]
    )
    assert slow["trajectory"][2]["wave_height_m"] == pytest.approx(sample["wave_height_m"])


@pytest.mark.parametrize("name", ["offshore", "outer"])
def test_curated_tracks_clear_whole_edge_mask(name):
    base = default_scenario()
    result = simulate(changed(base, route=next(r for r in ROUTES if r.id == name)))
    assert result["completed"], result["violation"]
    assert result["route_distance_m"] > 900 * 1852


def test_land_intersection_between_water_endpoints(hand):
    land = mapping(box(-129.1, 36, -128.9, 37))
    result = simulate(changed(hand, land=land))
    assert result["status"] == "infeasible"
    assert result["violation"]["code"] == "land_crossing"
    assert not result["completed"]


def test_horizon_overflow_is_not_calm(hand):
    result = simulate(
        changed(hand, departure=START + timedelta(hours=230), deadline=START + timedelta(hours=270))
    )
    assert result["status"] == "missing_coverage"
    assert result["eta"] is None
    assert result["elapsed_s"] == pytest.approx(10 * 3600)


def test_spatial_coverage_rejected(hand):
    env = hand.environment.model_dump()
    env["longitudes"] = [-128, -126, -122, -116]
    result = simulate(changed(hand, environment=env))
    assert result["status"] == "missing_coverage"
    assert result["fuel_kg"] == 0


def test_missing_fields_and_nan_rejected(hand):
    env = hand.environment.model_dump()
    del env["fields"]["wind_east_mps"]
    with pytest.raises(ValidationError):
        changed(hand, environment=env)
    with pytest.raises(ValidationError):
        changed(hand, daily_cost=float("nan"))
    with pytest.raises(ValidationError):
        changed(hand, speed_mps=25)
    with pytest.raises(ValidationError):
        changed(hand, departure="2026-09-11T00:00:00")


def test_step_convergence():
    base = default_scenario()
    a, b, c = [simulate(changed(base, max_step_s=step)) for step in (900, 450, 225)]
    for key in ("elapsed_s", "fuel_kg", "total_cost"):
        assert abs(a[key] - b[key]) / b[key] < 0.005
        assert abs(b[key] - c[key]) < abs(a[key] - b[key])


def test_step_shortens_at_time_boundaries_and_endpoint(hand):
    result = simulate(
        changed(hand, departure=START + timedelta(minutes=7), deadline=START + timedelta(days=2))
    )
    assert any(p["time"] == "2026-09-11T06:00:00Z" for p in result["trajectory"])
    assert result["trajectory"][-1]["lat"] == pytest.approx(hand.route.coordinates[-1][1])


def test_wave_threshold(hand):
    result = simulate(changed(hand, environment=load_environment("head-seas"), max_wave_m=3))
    assert result["status"] == "infeasible"
    assert result["violation"]["code"] == "wave_threshold"


def test_self_contained_replay_and_tamper_detection(hand):
    saved = ExportBundle(runs=[export_run(hand)])
    restored = ExportBundle.model_validate_json(saved.model_dump_json())
    assert replay(restored).runs[0].result == saved.runs[0].result
    edited = copy.deepcopy(saved)
    edited.runs[0].scenario.fuel_price_per_kg = 0.7
    with pytest.raises(ValueError, match="hashes"):
        replay(edited)
    edited = copy.deepcopy(saved)
    edited.runs[0].result["trajectory"][1]["fuel_kg"] += 1
    with pytest.raises(ValueError, match="Replay mismatch"):
        replay(edited)


def test_unknown_model_rejected(hand):
    run = export_run(hand)
    run.model_version = "future-model"
    with pytest.raises(ValueError, match="model version"):
        replay(ExportBundle(runs=[run]))


def test_step_shortens_at_spatial_grid_boundary(hand):
    result = simulate(hand)
    assert any(abs(p["lat"] - 38) < 1e-8 for p in result["trajectory"])


def test_mixed_inputs_in_comparison_are_rejected(hand):
    first = export_run(hand)
    second = export_run(changed(hand, speed_mps=12 * KNOT, daily_cost=15000))
    with pytest.raises(ValidationError, match="must share"):
        ExportBundle(runs=[first, second])
