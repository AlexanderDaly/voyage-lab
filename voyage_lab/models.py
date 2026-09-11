"""Validated SI inputs. These models contain no network or persistence logic."""

from datetime import datetime, timezone
from typing import Annotated, Literal

import numpy as np
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Number = Annotated[float, Field(allow_inf_nan=False)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Vessel(Model):
    name: str = Field(default="Meridian / synthetic cargo", max_length=80)
    version: Literal["fictional-cargo-1"] = "fictional-cargo-1"
    synthetic: Literal[True] = True
    reference_speed_mps: Number = Field(default=10 * 1852 / 3600, gt=0, le=15)
    reference_fuel_kg_s: Number = Field(default=20000 / 86400, gt=0, le=10)
    auxiliary_fuel_kg_s: Number = Field(default=2000 / 86400, ge=0, le=5)
    min_speed_mps: Number = Field(default=6 * 1852 / 3600, ge=0.5, le=15)
    max_speed_mps: Number = Field(default=18 * 1852 / 3600, gt=0.5, le=20)
    wave_loss_per_m2: Number = Field(default=0.012, ge=0, le=0.1)
    wind_loss_per_mps2: Number = Field(default=0.00015, ge=0, le=0.01)
    max_speed_loss: Number = Field(default=0.55, ge=0, le=0.9)

    @model_validator(mode="after")
    def speed_range(self):
        if not self.min_speed_mps <= self.reference_speed_mps <= self.max_speed_mps:
            raise ValueError("Reference speed must be inside the vessel speed range")
        return self


class Route(Model):
    id: str = Field(max_length=64)
    name: str = Field(max_length=100)
    coordinates: list[tuple[Number, Number]] = Field(min_length=2, max_length=100)

    @model_validator(mode="after")
    def wgs84(self):
        if any(not (-180 <= x <= 180 and -85 <= y <= 85) for x, y in self.coordinates):
            raise ValueError("Route positions must be WGS84 [longitude, latitude]")
        return self


FIELDS = {
    "current_east_mps",
    "current_north_mps",
    "wind_east_mps",
    "wind_north_mps",
    "wave_height_m",
    "wave_from_east",
    "wave_from_north",
}


class Environment(Model):
    id: str = Field(max_length=64)
    name: str = Field(max_length=100)
    kind: Literal["synthetic"] = "synthetic"
    source: str = Field(default="Voyage Lab deterministic fixture generator v1", max_length=200)
    issue_time: None = None
    retrieval_time: None = None
    attribution: str = Field(default="Original synthetic data, MIT", max_length=200)
    times: list[AwareDatetime] = Field(min_length=2, max_length=200)
    latitudes: list[Number] = Field(min_length=2, max_length=64)
    longitudes: list[Number] = Field(min_length=2, max_length=64)
    fields: dict[str, list[list[list[Number]]]]

    @model_validator(mode="after")
    def grid(self):
        self.times = [t.astimezone(timezone.utc) for t in self.times]
        for axis in (self.times, self.latitudes, self.longitudes):
            if any(a >= b for a, b in zip(axis, axis[1:])):
                raise ValueError("Environmental axes must be strictly increasing")
        if not (-85 <= self.latitudes[0] < self.latitudes[-1] <= 85):
            raise ValueError("Latitude coverage out of range")
        if not (-180 <= self.longitudes[0] < self.longitudes[-1] <= 180):
            raise ValueError("Longitude coverage out of range")
        expected = (len(self.times), len(self.latitudes), len(self.longitudes))
        if np.prod(expected) > 30000 or set(self.fields) != FIELDS:
            raise ValueError("Invalid field set or grid too large")
        for name, values in self.fields.items():
            arr = np.asarray(values)
            if arr.shape != expected or not np.isfinite(arr).all():
                raise ValueError(f"Invalid shape or nonfinite data for {name}")
            limit = 15 if name.startswith("current") else 100
            if np.any(np.abs(arr) > limit):
                raise ValueError(f"Out of bounds: {name}")
            if name == "wave_height_m" and np.any(arr < 0):
                raise ValueError("Wave height cannot be negative")
        for name in ("wave_from_east", "wave_from_north"):
            if np.any(np.abs(self.fields[name]) > 1):
                raise ValueError("Wave direction components must be in [-1, 1]")
        return self


class Scenario(Model):
    name: str = Field(default="West Coast passage", max_length=100)
    departure: AwareDatetime
    deadline: AwareDatetime
    speed_mps: Number = Field(gt=0, le=20)
    fuel_price_per_kg: Number = Field(default=0.6, ge=0, le=20)
    daily_cost: Number = Field(default=12000, ge=0, le=1000000)
    fixed_cost: Number = Field(default=0, ge=0, le=10000000)
    currency: Literal["USD"] = "USD"
    max_step_s: Number = Field(default=900, ge=30, le=900)
    max_wave_m: Number = Field(default=8, gt=0, le=30)
    vessel: Vessel
    route: Route
    environment: Environment
    land: dict

    @model_validator(mode="after")
    def valid_scenario(self):
        self.departure = self.departure.astimezone(timezone.utc)
        self.deadline = self.deadline.astimezone(timezone.utc)
        if not 0 < (self.deadline - self.departure).total_seconds() <= 30 * 86400:
            raise ValueError("Deadline must be after departure and within 30 days")
        if not self.vessel.min_speed_mps <= self.speed_mps <= self.vessel.max_speed_mps:
            raise ValueError("Speed is outside this vessel's supported range")
        return self


class CompareRequest(Model):
    scenario: Scenario
    speeds_mps: list[Number] = Field(min_length=1, max_length=7)

    @model_validator(mode="after")
    def ordered_speeds(self):
        if any(a >= b for a, b in zip(self.speeds_mps, self.speeds_mps[1:])):
            raise ValueError("Comparison speeds must be distinct and increasing")
        return self


class RunExport(Model):
    schema_version: Literal["1.0"] = "1.0"
    model_version: str
    source_revision: str
    implementation_sha256: str
    hashes: dict[str, str]
    scenario: Scenario
    result: dict


class ExportBundle(Model):
    bundle_version: Literal["1.0"] = "1.0"
    runs: list[RunExport] = Field(min_length=1, max_length=7)

    @model_validator(mode="after")
    def comparable(self):
        base = self.runs[0].scenario.model_dump(exclude={"speed_mps", "name"})
        if any(run.scenario.model_dump(exclude={"speed_mps", "name"}) != base for run in self.runs[1:]):
            raise ValueError(
                "Compared runs must share vessel, route, environment, land mask, costs, and settings"
            )
        speeds = [r.scenario.speed_mps for r in self.runs]
        if any(a >= b for a, b in zip(speeds, speeds[1:])):
            raise ValueError("Exported comparisons must use distinct increasing speeds")
        return self


def utc_string(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
