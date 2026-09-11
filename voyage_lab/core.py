"""Deterministic forward integration on WGS84 geodesics; no file or network I/O."""

import math
from datetime import timedelta

import numpy as np
from pyproj import Geod
from shapely.geometry import LineString, shape
from shapely.validation import explain_validity

from .models import Environment, Scenario, utc_string

GEOD = Geod(ellps="WGS84")
KNOT = 1852 / 3600


class ModelFailure(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


def fuel_rate(speed: float, vessel) -> float:
    return vessel.reference_fuel_kg_s * (speed / vessel.reference_speed_mps) ** 3 + vessel.auxiliary_fuel_kg_s


def ground_speed(water: float, east: float, north: float, bearing_deg: float) -> float:
    angle = math.radians(bearing_deg)
    along = east * math.sin(angle) + north * math.cos(angle)
    cross = east * math.cos(angle) - north * math.sin(angle)
    if abs(cross) > water:
        raise ModelFailure("cross_current", "Cross-current exceeds attainable through-water speed")
    speed = math.sqrt(max(0, water * water - cross * cross)) + along
    if speed <= 0:
        raise ModelFailure("no_progress", "Opposing current prevents forward progress")
    return speed


class Sampler:
    def __init__(self, snapshot: Environment):
        self.axes = [
            np.array([t.timestamp() for t in snapshot.times]),
            np.array(snapshot.latitudes),
            np.array(snapshot.longitudes),
        ]
        self.fields = {name: np.asarray(values) for name, values in snapshot.fields.items()}

    def sample(self, lon: float, lat: float, time: float) -> dict:
        indices, weights = [], []
        for axis, value in zip(self.axes, (time, lat, lon)):
            if value < axis[0] - 1e-7 or value > axis[-1] + 1e-7:
                raise ModelFailure(
                    "missing_coverage", "Position or simulated time is outside environmental coverage"
                )
            i = min(len(axis) - 2, max(0, int(np.searchsorted(axis, value, side="right")) - 1))
            indices.append(i)
            weights.append(float(np.clip((value - axis[i]) / (axis[i + 1] - axis[i]), 0, 1)))
        t, y, x = indices
        wt, wy, wx = weights
        output = {}
        for name, arr in self.fields.items():
            v = arr[t : t + 2, y : y + 2, x : x + 2]
            output[name] = float(np.einsum("i,j,k,ijk->", [1 - wt, wt], [1 - wy, wy], [1 - wx, wx], v))
        return output

    def next_boundary(self, time: float) -> float:
        i = int(np.searchsorted(self.axes[0], time + 1e-6, side="right"))
        return float(self.axes[0][i]) if i < len(self.axes[0]) else time

    def spatial_step(self, start, bearing, progressed, speed, dt):
        """Shorten at a crossed grid line, solving on the same geodesic."""
        lon, lat, _ = GEOD.fwd(*start, bearing, progressed)
        end_lon, end_lat, _ = GEOD.fwd(*start, bearing, progressed + speed * dt)
        for component, axis, value, end in ((0, self.axes[2], lon, end_lon), (1, self.axes[1], lat, end_lat)):
            rising = end > value
            candidates = (
                axis[(axis > value + 1e-8) & (axis < end)]
                if rising
                else axis[(axis < value - 1e-8) & (axis > end)]
            )
            if not len(candidates):
                continue
            boundary = min(candidates) if rising else max(candidates)
            low, high = 0.0, dt
            for _ in range(40):
                mid = (low + high) / 2
                coord = GEOD.fwd(*start, bearing, progressed + speed * mid)[component]
                if (coord < boundary) == rising:
                    low = mid
                else:
                    high = mid
            dt = (low + high) / 2
        return dt


def effective_water_speed(scenario: Scenario, env: dict, bearing: float) -> float:
    # Relative weather is measured against track bearing, not crabbed bow heading.
    # Wind components describe motion TO; wave direction components point FROM.
    a = math.radians(bearing)
    east, north = math.sin(a), math.cos(a)
    headwind = max(0, -(env["wind_east_mps"] * east + env["wind_north_mps"] * north))
    wave_norm = math.hypot(env["wave_from_east"], env["wave_from_north"])
    headsea = (
        max(0, (env["wave_from_east"] * east + env["wave_from_north"] * north) / wave_norm)
        if wave_norm > 1e-9
        else 0
    )
    v = scenario.vessel
    loss = min(
        v.max_speed_loss,
        v.wave_loss_per_m2 * env["wave_height_m"] ** 2 * (0.25 + 0.75 * headsea)
        + v.wind_loss_per_mps2 * headwind**2,
    )
    return scenario.speed_mps * (1 - loss)


def route_legs(scenario: Scenario):
    try:
        land = shape(scenario.land)
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("Invalid land geometry") from exc
    if land.geom_type not in ("Polygon", "MultiPolygon") or not land.is_valid:
        raise ValueError(f"Invalid land polygons: {explain_validity(land)}")
    # This regional model intentionally excludes arbitrary world-wide routing.
    points = scenario.route.coordinates
    if any(not (-130 <= lon <= -116 and 30 <= lat <= 50) for lon, lat in points):
        raise ValueError("Route is outside the supported West Coast bounds")
    legs = []
    for start, end in zip(points, points[1:]):
        bearing, _, distance = GEOD.inv(*start, *end)
        if distance < 1:
            raise ValueError("Consecutive route points must be at least one metre apart")
        # Whole-edge intersections on a geodesic densified to at most 1 km.
        dense = [start, *GEOD.npts(*start, *end, max(1, math.ceil(distance / 1000) - 1)), end]
        if LineString(dense).intersects(land):
            raise ModelFailure("land_crossing", "A route edge intersects the bundled regional land mask")
        legs.append((start, end, bearing, distance))
    return legs


def simulate(scenario: Scenario) -> dict:
    sampler = Sampler(scenario.environment)
    elapsed, fuel, distance_total = 0.0, 0.0, 0.0
    trajectory = []
    rate = fuel_rate(scenario.speed_mps, scenario.vessel)
    total_distance = 0.0

    def result(status, violation=None):
        finished = status in ("completed", "deadline_exceeded")
        return {
            "status": status,
            "violation": violation,
            "completed": finished,
            "elapsed_s": elapsed,
            "distance_m": distance_total,
            "route_distance_m": total_distance,
            "eta": utc_string(scenario.departure + timedelta(seconds=elapsed)) if finished else None,
            "fuel_kg": fuel,
            "fuel_cost": fuel * scenario.fuel_price_per_kg,
            "time_cost": elapsed / 86400 * scenario.daily_cost,
            "fixed_cost": scenario.fixed_cost,
            "total_cost": fuel * scenario.fuel_price_per_kg
            + elapsed / 86400 * scenario.daily_cost
            + scenario.fixed_cost,
            "deadline_met": finished and status == "completed",
            "trajectory": trajectory,
        }

    try:
        legs = route_legs(scenario)
        total_distance = sum(leg[3] for leg in legs)
        for start, end, bearing, length in legs:
            progressed = 0.0
            while length - progressed > 1e-6:
                if len(trajectory) >= 50000 or elapsed > 30 * 86400:
                    raise ModelFailure(
                        "integration_limit", "Simulation exceeded its bounded integration budget"
                    )
                lon, lat, _ = GEOD.fwd(*start, bearing, progressed)
                now = scenario.departure.timestamp() + elapsed
                env = sampler.sample(lon, lat, now)
                # Recompute the forward bearing along the ellipsoidal geodesic.
                local_bearing = GEOD.inv(lon, lat, *end)[0]
                if env["wave_height_m"] > scenario.max_wave_m:
                    raise ModelFailure(
                        "wave_threshold", "Wave height exceeds the experimental scenario threshold"
                    )
                water = effective_water_speed(scenario, env, local_bearing)
                speed = ground_speed(water, env["current_east_mps"], env["current_north_mps"], local_bearing)
                dt = min(scenario.max_step_s, (length - progressed) / speed, sampler.next_boundary(now) - now)
                dt = sampler.spatial_step(start, bearing, progressed, speed, dt)
                if dt <= 1e-7:
                    raise ModelFailure(
                        "missing_coverage", "Environmental horizon ends before voyage completion"
                    )
                if not trajectory:
                    trajectory.append(
                        {
                            "time": utc_string(scenario.departure),
                            "elapsed_s": 0,
                            "lon": lon,
                            "lat": lat,
                            "distance_m": 0,
                            "fuel_kg": 0,
                            "cost": scenario.fixed_cost,
                            "ground_speed_mps": speed,
                            "wave_height_m": env["wave_height_m"],
                        }
                    )
                # Forward Euler. Each stored sample describes the preceding step's forcing.
                step_distance = min(length - progressed, speed * dt)
                next_lon, next_lat, _ = GEOD.fwd(*start, bearing, progressed + step_distance)
                endpoint = sampler.sample(next_lon, next_lat, now + dt)
                if endpoint["wave_height_m"] > scenario.max_wave_m:
                    raise ModelFailure(
                        "wave_threshold", "Wave height exceeds the experimental scenario threshold"
                    )
                progressed += step_distance
                elapsed += dt
                fuel += rate * dt
                distance_total += step_distance
                lon, lat = next_lon, next_lat
                trajectory.append(
                    {
                        "time": utc_string(scenario.departure + timedelta(seconds=elapsed)),
                        "elapsed_s": elapsed,
                        "lon": lon,
                        "lat": lat,
                        "distance_m": distance_total,
                        "fuel_kg": fuel,
                        "cost": fuel * scenario.fuel_price_per_kg
                        + elapsed / 86400 * scenario.daily_cost
                        + scenario.fixed_cost,
                        "ground_speed_mps": speed,
                        "wave_height_m": env["wave_height_m"],
                    }
                )
        late = scenario.departure + timedelta(seconds=elapsed) > scenario.deadline
        return result(
            "deadline_exceeded" if late else "completed", "Arrival is after the deadline" if late else None
        )
    except ModelFailure as exc:
        status = (
            "missing_coverage"
            if exc.code == "missing_coverage"
            else "numerical_failure"
            if exc.code == "integration_limit"
            else "infeasible"
        )
        return result(status, {"code": exc.code, "message": exc.message})
