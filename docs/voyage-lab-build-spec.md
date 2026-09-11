# Voyage Lab — open-source voyage simulation

Portfolio build specification · 11 September 2026

Status: proposed implementation; no application or benchmark results have been produced yet. “Voyage Lab” is a working title.

## The project

Build a reproducible maritime simulation workbench that compares routes, departure times, vessel speeds, fuel consumption, and voyage costs. Its central question is: **Which route and speed plan meets an arrival deadline at the lowest modeled cost, under changing weather?**

This suits a Python/Linux and systems portfolio because the visible application rests on numerical simulation, geospatial data processing, constrained optimization, and reproducible experiments. The deliverable should demonstrate both software craftsmanship and the ability to explain where a model is reliable.

Sofar's public product describes vessel selection, route input, speed/power/arrival adjustments, and side-by-side voyage economics. It also describes proprietary observations, operationally updated vessel models, and ChartWorld routing. These establish the inspiration and the capabilities that a public-data prototype cannot claim to reproduce. [Sofar product description](https://www.sofarocean.com/products/wayfinder/solutions/voyage-simulator)

Use an original interface and project identity. Present this as a research and portfolio simulator. It will not validate navigability, vessel safety, or commercial voyage estimates.

## The first demonstrable experience

Open a saved US West Coast example. Select a fictional cargo vessel, departure time, arrival deadline, and user-entered fuel and daily operating costs. Compare a baseline with slower and faster scenarios. The map shows candidate tracks; charts show the vessel's progress through weather and accumulated fuel. Selecting a scenario exposes its assumptions and cost breakdown. Export enough information to reproduce the calculation offline.

Start with one offshore corridor between the approaches to Seattle and Los Angeles. Treat the endpoints as explicitly marked offshore gates. Show port names for orientation, but exclude berth access, pilotage, traffic schemes, and harbor transit from the simulated track. Do not connect inland port coordinates to offshore tracks with unvalidated straight lines. Add other corridors only after the first passes geometric and numerical checks.

## Scope and release boundaries

| Capability | v0.1: simulator | v0.2: portfolio release |
| --- | --- | --- |
| Vessel model | One editable, explicitly synthetic vessel | Additional profiles and model comparison |
| Geography | One bounded corridor, curated alternate tracks | Regional water graph with exclusions |
| Scenario controls | Departure, constant speed, arrival deadline, costs | Speed choices by segment and optimized route |
| Environment | Offline fixtures, then cached forecast inputs | Repeatable forecast snapshots and sensitivity experiments |
| Outputs | ETA, elapsed time, fuel, cost, constraint flags | Trade-off frontier, optimization diagnostics, robustness results |
| Interface | Route map, scenario table, time-series charts | Weather playback and optimization comparison |
| Reproducibility | JSON import/export and CLI | Benchmark runner, data manifests, documented release |

Defer fleet dispatch, live AIS, berth scheduling, canal rules, real-time fuel-price feeds, compliance accounting, full hydrodynamics, automatic vessel calibration, reinforcement learning, and conversational controls. Each can become a later extension once the baseline is useful.

## Reuse versus original work

52°North's Weather Routing Tool is an existing Python project for weather-dependent fuel routing, with an MIT license. Its maintainers describe routing algorithms, environmental-data handling, and constraint support. Inspect its sample workflow during a short feasibility spike. Use an adapter to evaluate it as an optional routing backend or comparison engine. [Repository](https://github.com/52North/WeatherRoutingTool), [maintainer overview](https://52north.org/software/software-components/weather-routing-tool/), [example sandbox](https://github.com/52North/WRT-sandbox)

Keep a small original simulator with an explicit mathematical contract. That makes the economics, regression tests, and model assumptions reviewable. Your portfolio contribution is the scenario model, numerical implementation, data provenance, comparison workflow, and experimental evaluation. Document which parts come from upstream software.

Timebox the upstream spike to one or two working days. Success means reproducing one example, identifying its required inputs, and exporting route geometry plus metrics. If its integration dominates the work, ship the standalone simulator first and retain the adapter boundary. Do not build a second full weather-routing framework merely to avoid using dependencies.

`searoute-py` is useful for generating approximate maritime route visualizations, but its README explicitly excludes real navigation use. Treat any generated track as a candidate requiring checks against the demo's supported geographic constraints. It is not a safety or navigability validator. [Project README](https://github.com/genthalili/searoute-py)

## Proposed architecture

| Component | Initial choice | Responsibility |
| --- | --- | --- |
| Scientific core | Python, NumPy, SciPy | Pure simulation functions, cost integration, solver |
| Geospatial layer | Shapely, pyproj | Coordinate operations, geodesic distance, edge checks |
| Environment layer | xarray; cfgrib when GRIB is introduced | Normalize and sample environmental fields |
| Service | FastAPI with typed request/response models | Validate scenarios and expose simulation results |
| Interface | React, TypeScript, MapLibre GL JS | Map, input controls, scenario comparisons, playback |
| Persistence | SQLite plus immutable data files | Scenarios, run metadata, cached inputs |
| Distribution | Python CLI and Docker Compose | Reproduce runs without the web interface; start the demo |
| Verification | pytest and browser smoke tests | Numerical behavior, constraints, and one complete user workflow |

MapLibre GL JS provides a browser mapping renderer. Select and attribute the basemap independently; a renderer does not provide an unrestricted tile service. An offline demo should bundle a suitably licensed, small regional map asset. [MapLibre documentation](https://maplibre.org/maplibre-gl-js/docs/)

The dependency direction is interface → API → core; the core must run without a server or network. Begin with a single backend process. Introduce a bounded worker only when optimization makes requests slow. Add Redis, distributed scheduling, or a spatial database only for a demonstrated requirement.

Proposed repository layout: `core/`, `api/`, `web/`, `data/fixtures/`, `benchmarks/`, `tests/`, and `docs/`. Include a README, license, contribution instructions, model assumptions, third-party notices, and one reproducible case study.

## Data acquisition and provenance

| Input | Initial approach | Required handling |
| --- | --- | --- |
| Waves and currents | Open-Meteo Marine API | Save actual response, units, coverage, and requested model |
| Wind | Separate atmospheric forecast adapter | Keep its timestamps and coverage aligned with marine inputs |
| Later gridded ingestion | NOAA GFS atmosphere and GFS Wave through NOMADS | Select a bounded region and forecast cycle; preserve source files |
| Vessel performance | Fictional, documented configuration | Display synthetic status on every result |
| Costs | User-entered assumptions | Currency, timestamp, and cost basis; no claim of live market prices |
| Land/exclusions | Attributed regional polygon dataset | Version the geometry and state its resolution limits |
| Demo data | Small synthetic fixtures first | Deterministic, redistributable, and usable without credentials |

Open-Meteo's Marine API documents wave and current variables. Wave directions describe where waves come from; current directions describe where the flow goes. Normalize these conventions before computing relative headings. The documentation lists model-dependent coverage, so determine the usable horizon from the actual responses rather than a hardcoded maximum. [Marine API documentation](https://open-meteo.com/en/docs/marine-weather-api)

Its hosted free service is for non-commercial use and has request limits; data attribution is required. Keep the hosted service conditions distinct from the license of your own code. Review the applicable tier before operating a commercial deployment. [Open-Meteo pricing](https://open-meteo.com/en/pricing), [data and service overview](https://open-meteo.com/)

NOAA lists both GFS atmospheric products and GFS Wave, while NOMADS offers access to model products and GRIB filtering. Treat direct GRIB ingestion as a later pipeline milestone. [NOAA product catalog](https://www.nco.ncep.noaa.gov/pmb/products/gfs/), [NOMADS](https://nomads.ncep.noaa.gov/)

Every environmental snapshot should record source, requested model, issue time when supplied, retrieval time, valid times, spatial coverage, units, attribution, and content hash. A retrieval timestamp is not a model issue timestamp. Store unavailable metadata as unknown. For point APIs, preserve returned grid coordinates as well as requested coordinates.

The simulator must distinguish `synthetic`, `forecast`, and `retrospective` runs. Reject missing environmental coverage or offer an explicit, separately labeled calm-water scenario. Never silently fill an absent forecast with zero wind, zero current, or the last available hour. Cache and batch requests; a slider movement must not trigger a fresh network request per segment.

## Simulation contract

All formulas below define the proposed baseline model. They are implementation assumptions, not calibrated ship-performance claims.

Use SI units internally, UTC timestamps, and WGS84 positions. Convert speed to knots and distance to nautical miles for display. Every input has an explicit unit and finite numerical bounds.

### Calm-water propulsion

Let `v` be commanded speed through water, `v_ref` reference speed, `q_ref` reference propulsion fuel rate, and `q_aux` auxiliary fuel rate:

`q_prop(v) = q_ref × (v / v_ref)^3`

`q_total(v) = q_prop(v) + q_aux`

This is a deliberately simplified baseline over the vessel's configured speed range. It is not a universal engine curve. Reject speeds outside the supported range. Keeping auxiliary consumption separate prevents the model from treating arbitrarily slow travel as free.

### Environment and progress

In the first weather-aware model, define a transparent, bounded wave/wind speed-loss function. It reduces attainable through-water speed at the selected propulsion setting; the fuel rate remains tied to that setting. Store its coefficients and label them synthetic. A later resistance/power model may replace it, but do not apply both approaches in a way that double-counts the same weather penalty.

Resolve current into along-track and cross-track components. Under a simplified track-holding model, attainable ground speed is:

`v_ground = sqrt(v_water_effective^2 - current_cross^2) + current_along`

Reject the transition if cross-current exceeds attainable through-water speed, or ground speed is nonpositive. This baseline omits rudder drag and maneuvering losses. Include those omissions in the model documentation.

Split track segments into short integration steps. At each step, sample environmental conditions at the vessel's position and current simulated time, calculate progress, and integrate fuel and elapsed time. Start with a configurable maximum step of 15 minutes and demonstrate convergence when halved. Shorten a step at segment ends and data boundaries. Interpolate directional quantities through vectors rather than averaging angles across north.

Changing speed changes arrival at every subsequent location and therefore the weather encountered. Recompute the forward trajectory; do not score every waypoint using departure-time weather.

### Economics

`fuel_cost = fuel_mass × fuel_price`

`time_cost = elapsed_days × daily_cost`

`total_cost = fuel_cost + time_cost + entered_fixed_costs`

Define elapsed time from departure at the first offshore gate to arrival at the final gate. In v0.1 there is no implicit port waiting or port fuel consumption. Daily cost represents one user-selected basis, such as hire or operating cost; do not count overlapping expenses twice. Use a hard arrival deadline for constrained optimization. A configurable lateness penalty can be a separate future scenario mode.

Keep optional emissions separate from cost. If added, require an attributed fuel-specific factor and label the result tank-to-wake CO2; do not call it lifecycle emissions or compliance accounting.

### Hand-checkable fixture

A hypothetical 240-nautical-mile calm-water route at 10 knots takes 24 hours. If reference propulsion use is 20 tonnes/day at 10 knots and auxiliary use is 2 tonnes/day, the model must consume 22 tonnes. At an illustrative $600/tonne and $12,000/day time cost, total modeled cost is $25,200 before fixed costs. These are test inputs, not market prices or real vessel specifications.

## Optimization

First enumerate a small set of curated tracks and constant-speed choices. This gives an understandable baseline, immediate scenario comparisons, and a correctness oracle for small problems.

For v0.2, use a regional graph with states containing location and arrival-time information; actions select a next edge and speed. Environmental edge costs depend on departure time. A distance-only shortest-path calculation cannot solve that objective.

Use an explicit time-expanded graph or a documented multi-label method. If discretizing time, specify how transitions are represented, account for any modeled waiting, and measure sensitivity to time resolution. Do not silently round arrival times into free waiting or discard all but the earliest arrival when optimizing fuel. Report optimality only for the implemented discrete model and search bounds.

Objective: minimize modeled fuel plus time costs while satisfying deadline, configured environmental thresholds, and supported geographic exclusions. Validate complete edge geometry against the land mask; checking endpoints alone is insufficient. Treat thresholds as experimental model constraints, not proof of vessel safety. Validate optimized outputs with the same forward simulator used for baseline routes.

Expose a trade-off frontier: the set of scenarios for which improving cost would require worsening time or another selected metric. Show the reference scenario and the exact calculation of relative savings. A negative saving is a legitimate result. If no feasible solution exists, return that result with the violated constraint; do not invent a route.

## Interface and API

Use one primary screen: voyage inputs at left, a central map, scenario results alongside it, and a time slider below. Highlight the selected track and offer charts for speed, waves, cumulative fuel, and cumulative cost. Clearly distinguish replay data from a forecast. Display data coverage and synthetic vessel status close to the results.

Suggested API contract:

| Operation | Purpose |
| --- | --- |
| `GET /vessels` | Return versioned vessel configurations |
| `GET /routes` | Return supported corridors and candidate tracks |
| `POST /simulate` | Simulate a complete, validated scenario |
| `POST /compare` | Evaluate scenarios against the same input snapshot |
| `POST /optimize` | Start a bounded optimization job |
| `GET /jobs/{id}` | Return job status, progress, and failure details |
| `GET /runs/{id}/export` | Export a reproducibility manifest and results |

Each run records a schema version, source revision, vessel-model version, route geometry hash, environmental snapshot hash, inputs, integration settings, and seed where relevant. Exports include the trajectory and all headline metrics. Separate infeasible scenarios from invalid requests and numerical failures.

## Verification and portfolio evidence

| Test or experiment | What it establishes |
| --- | --- |
| Hand-calculated calm-water fixture | Correct units, elapsed time, fuel integration, and cost accounting |
| Following, opposing, and cross-current fixtures | Correct direction conventions and track-holding feasibility |
| Storm moving across the route | Weather sampling depends on arrival time |
| Land-crossing and disconnected-region cases | Whole-edge checks and explicit infeasibility |
| Missing coverage and horizon overflow | No silent fabricated forecast |
| Smaller integration step | Numerical convergence within a stated tolerance |
| Exhaustive tiny graph compared with optimizer | Correct discrete objective and constraint handling |
| Baseline included in optimizer candidates | Reported best feasible result does not lose the available baseline |
| Fixed manifest replay | Results reproduce within a stated numerical tolerance |
| One complete browser workflow | Scenario creation, comparison, selection, and export work together |

Publish separate results for implementation correctness, model sensitivity, and empirical accuracy. Real forecast inputs alone do not validate fuel estimates. Without measured vessel performance and fuel data, report model-relative improvements only.

Use a fixed suite containing calm conditions, persistent head seas, a moving storm, favorable and opposing currents, and an infeasible deadline. Record time, fuel, cost, violated constraints, runtime, hardware, and model/data versions. Add ablations that remove weather dependence or speed optimization to show what each component contributes.

For historical experiments, distinguish forecasts available at the decision time from later analyses. Optimizing against weather that was only known afterward is a hindsight experiment. If an archive does not preserve forecast vintage, do not use it to claim forecast-based operational performance.

Add uncertainty only after deterministic results are correct. Use coherent weather scenarios or available ensemble members. Independent random noise at every point produces implausible weather. Synthetic perturbations support sensitivity ranges; calibrated arrival probabilities require appropriate forecast ensembles and validation.

## Delivery sequence and effort

Planning estimate: roughly 120–200 focused hours for a polished, bounded portfolio release, depending on data integration and interface work. This is an estimate rather than a deadline; actual vessel calibration is outside it.

| Milestone | Completion criterion |
| --- | --- |
| 1. Baseline and dependency spike | CLI reproduces the hand calculation; upstream example assessed |
| 2. Environmental simulation | One corridor runs against versioned fixtures with trajectory output |
| 3. Scenario application | Inputs, map, comparison, and export complete one working flow |
| 4. Forecast adapter | Cached source responses, coverage validation, and offline replay |
| 5. Regional optimization | Feasible route/speed comparison; tiny-graph correctness evidence |
| 6. Portfolio release | Documented install, bounded demo, benchmark report, short walkthrough |

Aim to complete milestones 1–3 before expanding scope. A strong initial acceptance criterion is: **a new contributor can reproduce a saved voyage comparison without credentials and explain every displayed number from the exported inputs.**

Use a provisional latency target of under one second for one cached scenario and under ten seconds for the bounded regional optimization on a documented machine. These are targets to measure, not claims of achieved performance. Keep forecast acquisition outside those timings and report its latency separately.

Prefer MIT or Apache-2.0 for original code, with dependency and dataset notices retained under their own terms. Ship original synthetic fixtures and redistributable assets; provide acquisition scripts for external data where appropriate. A public repository, a two-minute demonstration, and a measured technical case study are the final portfolio package.

Suggested future portfolio description, to use only after implementation: “Built an open-source voyage simulator combining time-dependent environmental data, vessel performance modeling, and constrained route optimization, with reproducible benchmarks and an interactive scenario workbench.” Replace broad adjectives with measured results once available.
