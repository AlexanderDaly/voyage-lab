# Scientific model v1

This document describes implemented behavior. The original build specification describes the wider research direction.

## Units and boundaries

All numerical inputs are finite and bounded. Internal distance is metres, speed metres/second, time seconds, fuel kilograms, and propulsion rates kilograms/second. Positions are WGS84 `[longitude, latitude]`. One nautical mile is exactly 1852 m; one knot is 1852/3600 m/s. Display uses nautical miles, knots, tonnes, hours, and USD. Timestamps require timezone information and normalize to UTC.

The supported regional bounds are longitude -130 to -116 and latitude 30 to 50. The two curated tracks run from (-125.4, 48.1) to (-119.1, 33.3), offshore of the named ports. There are no port connectors, berth access, port waiting, or harbor fuel. Arbitrary imported regional tracks are experimental inputs; passing checks does not establish navigability.

Land checks use Shapely intersection of whole geodesic edges densified to at most 1 km against a clipped Natural Earth 1:50m polygon mask. Boundary touching is rejected. Geometry resolution, missing small hazards, bathymetry, traffic lanes, territorial rules, and vessel clearance are outside the model. The bundled map is an orientation surface, not a navigational chart.

## Propulsion and weather

Commanded propulsion setting is expressed as a calm-water speed `v`:

```text
q_prop = q_ref * (v / v_ref)^3
q_total = q_prop + q_aux
```

The fictional default has `v_ref = 10 kn`, `q_ref = 20 t/day`, `q_aux = 2 t/day`, and a supported 6–18 kn range. The UI compares a baseline of 8–16 kn with alternatives 2 kn below and above it. Reference speed and consumption are editable; this does not calibrate the model.

Currents and winds are east/north vectors describing motion **to** a direction. Wave vectors point **from** the wave source. Let `u` be the unit vector along the local track bearing, `H` significant wave height, `W` wind velocity, and `D` the interpolated wave-from direction:

```text
headwind = max(0, -dot(W, u))
headsea = max(0, dot(normalize(D), u))
loss = min(0.55, 0.012 * H^2 * (0.25 + 0.75 * headsea)
                 + 0.00015 * headwind^2)
v_water_effective = v * (1 - loss)
```

Coefficients are synthetic, dimensioned to produce a dimensionless loss. A near-zero interpolated direction vector contributes zero headsea factor; the base wave penalty remains. Relative weather is measured against track bearing, not the crabbed bow heading. This is an explicit simplification. The coefficients and loss bound travel with the vessel definition in every export.

Fuel remains tied to the commanded setting. No second resistance/power penalty is added. Track holding uses the current components parallel and perpendicular to the track:

```text
v_ground = sqrt(v_water_effective^2 - current_cross^2) + current_along
```

Cross-current greater than attainable water speed or nonpositive ground speed makes the transition infeasible. Rudder drag, maneuvering losses, acceleration, engine limits beyond the configured speed range, and hull-specific responses are omitted.

## Environment and integration

Fixtures are gridded at 6-hour intervals over 11 September 2026 00:00 UTC through 21 September 2026 00:00 UTC, with latitude/longitude axes embedded in each JSON file. They are analytic synthetic fields, not measured or forecast products. The moving storm travels south while changing the weather encountered at each simulated arrival time.

Sampling is trilinear in time, latitude, and longitude. Directional data is interpolated as vector components. No extrapolation, nearest-hour carry-forward, or missing-value substitution is allowed. Only `synthetic` inputs are supported in v0.1; forecast and retrospective adapters must introduce and validate their own provenance contract later.

Forward Euler integrates progress, elapsed time, and fuel, recomputing position, local geodesic bearing, environment, and speed each step. The default maximum is 900 seconds. Steps shorten at route endpoints, environmental time boundaries, and crossed spatial grid lines. A bisection on geodesic position finds spatial crossings. Environmental coverage and wave threshold are checked at step start and end. Continuous extrema within a step are not exhaustively constrained; finer steps reduce this limitation.

Each trajectory row after the initial point stores the endpoint's cumulative distance, elapsed time, fuel, and cost. Its ground speed and wave height describe the forcing used over the **preceding** integration step. Plots connect these recorded samples for inspection. A numerical budget limits a run to 50,000 trajectory samples or 30 days.

Acceptance: halving 900 to 450 seconds changes elapsed time, fuel, and cost by less than 0.5% on the default moving-storm case, and a further halving to 225 seconds reduces the difference. This is a bounded convergence experiment, not a universal error bound.

## Economics and outcomes

```text
fuel_cost = fuel_kg * fuel_price_per_kg
time_cost = elapsed_s / 86400 * daily_cost
total_cost = fuel_cost + time_cost + fixed_cost
```

Daily cost represents one user-selected basis; do not enter overlapping hire and operating costs twice. Fixed costs are entered once. The model includes no emissions, compliance costs, market prices, penalties, or implicit waiting.

| Outcome | Meaning |
| --- | --- |
| HTTP 422 / CLI input error | Invalid or unsupported scenario |
| `completed` | Full voyage, arrival on or before deadline |
| `deadline_exceeded` | Full voyage, late; retain all metrics |
| `infeasible` | Land intersection, unholdable track, no progress, or experimental wave threshold |
| `missing_coverage` | Required environmental position/time is unavailable |
| `numerical_failure` | Integration budget exhausted |

Incomplete runs have no ETA and expose only accumulated partial metrics. Their cost is not eligible for the best-feasible comparison. Unexpected software exceptions remain server errors; they are not disguised as physical infeasibility.

## Replay contract

Bundle/schema version is `1.0`; scientific model is `synthetic-track-holding-1`. Each run embeds all input dependencies, trajectory, headline metrics, model identifier, scientific source fingerprint, source revision when Git is available, and SHA-256 hashes of route, environment, vessel, land, and the complete scenario. Unknown revision metadata is reported as unavailable. A dirty working tree is labeled `+dirty`.

Run inputs in a comparison must be identical except for speed and display name, with distinct increasing speeds. The reference is the middle index (`floor(count/2)`); browser comparisons always have three speeds. All runs are recomputed on import. Input hash mismatch, unsupported versions, structural mismatch, or result mismatch rejects replay. Numerical fields use relative tolerance 1e-9 and absolute tolerance 1e-6 in their SI units; timestamp strings and categorical fields must match exactly. Cross-platform floating-point and timestamp behavior requires CI evidence before claiming cross-platform replay.

Hashes establish content identity, not authenticity or scientific validity. An imported land mask is part of that experiment's assumptions. A modified fixture may be a valid new experiment, but cannot masquerade as an unchanged verified export.
